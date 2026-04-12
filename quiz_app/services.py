import json
import re
import tempfile
from functools import lru_cache
from pathlib import Path

import whisper
from django.conf import settings
from django.db import transaction
from google import genai
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator, model_validator
from yt_dlp import YoutubeDL

from quiz_app.models import Quiz, Question, extract_youtube_video_id, build_canonical_youtube_url


class QuizGenerationError(Exception):
    pass


class GeneratedQuestionSchema(BaseModel):
    question_title: str = Field(min_length=1, max_length=255)
    question_options: list[str]
    answer: str = Field(min_length=1, max_length=255)

    @field_validator('question_options')
    @classmethod
    def validate_question_options(cls, value):
        cleaned_options = [option.strip() for option in value]

        if len(cleaned_options) != 4:
            raise ValueError('Each question must have exactly 4 options.')

        if len(set(cleaned_options)) != 4:
            raise ValueError('Each question option must be unique.')

        if any(not option for option in cleaned_options):
            raise ValueError('Question options must not be empty.')

        return cleaned_options

    @field_validator('question_title')
    @classmethod
    def validate_question_title(cls, value):
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError('Question title must not be empty.')
        return cleaned_value

    @field_validator('answer')
    @classmethod
    def validate_answer(cls, value):
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError('Answer must not be empty.')
        return cleaned_value

    @model_validator(mode='after')
    def validate_answer_in_options(self):
        if self.answer not in self.question_options:
            raise ValueError('Answer must be one of the question options.')
        return self


class GeneratedQuizSchema(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=150)
    questions: list[GeneratedQuestionSchema]

    @field_validator('title')
    @classmethod
    def validate_title(cls, value):
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError('Title must not be empty.')
        return cleaned_value

    @field_validator('description')
    @classmethod
    def validate_description(cls, value):
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError('Description must not be empty.')
        if len(cleaned_value) > 150:
            raise ValueError('Description must not exceed 150 characters.')
        return cleaned_value

    @field_validator('questions')
    @classmethod
    def validate_questions(cls, value):
        if len(value) != 10:
            raise ValueError('Exactly 10 questions are required.')
        return value


def strip_markdown_code_fences(value):
    cleaned_value = value.strip()
    cleaned_value = re.sub(r'^```json\s*', '', cleaned_value, flags=re.IGNORECASE)
    cleaned_value = re.sub(r'^```\s*', '', cleaned_value)
    cleaned_value = re.sub(r'\s*```$', '', cleaned_value)
    return cleaned_value.strip()


@lru_cache(maxsize=1)
def get_whisper_model():
    model_name = getattr(settings, 'WHISPER_MODEL', 'base')
    return whisper.load_model(model_name)


def download_youtube_audio(video_url, output_dir):
    output_template = str(Path(output_dir) / 'audio.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'noplaylist': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as exc:
        raise QuizGenerationError('Could not download the YouTube audio.') from exc

    audio_files = sorted(Path(output_dir).glob('audio.*'))

    if not audio_files:
        raise QuizGenerationError('No audio file was downloaded.')

    return str(audio_files[0])


def transcribe_audio_file(audio_path):
    try:
        model = get_whisper_model()
        result = model.transcribe(audio_path)
    except Exception as exc:
        raise QuizGenerationError('Could not transcribe the audio file.') from exc

    transcript = result.get('text', '').strip()

    if not transcript:
        raise QuizGenerationError('Transcript is empty.')

    return transcript


def build_quiz_prompt(transcript):
    return f"""
Based on the following transcript, generate a quiz in valid JSON format.

The quiz must follow this exact structure:

{{
    "title": "Create a concise quiz title based on the topic of the transcript.",
    "description": "Summarize the transcript in no more than 150 characters. Do not include any quiz questions or answers.",
    "questions": [
    {{
        "question_title": "The question goes here.",
        "question_options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": "The correct answer from the above options"
    }}
    ]
}}

Requirements:
- Create exactly 10 questions.
- Each question must have exactly 4 distinct answer options.
- Only one correct answer is allowed per question, and it must be present in "question_options".
- The output must be valid JSON and parsable as-is.
- Do not include explanations, comments, markdown, or any text outside the JSON.

Transcript:
{transcript}
""".strip()


def generate_quiz_data_from_transcript(transcript):
    api_key = getattr(settings, 'GEMINI_API_KEY', None)

    if not api_key:
        raise QuizGenerationError('GEMINI_API_KEY is missing.')

    prompt = build_quiz_prompt(transcript)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash'),
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_json_schema': GeneratedQuizSchema.model_json_schema(),
            },
        )
    except Exception as exc:
        raise QuizGenerationError('Could not generate quiz content with Gemini.') from exc

    response_text = getattr(response, 'text', '') or ''

    if not response_text.strip():
        raise QuizGenerationError('Gemini returned an empty response.')

    cleaned_response_text = strip_markdown_code_fences(response_text)

    try:
        return GeneratedQuizSchema.model_validate_json(cleaned_response_text)
    except PydanticValidationError as exc:
        raise QuizGenerationError(f'Generated quiz data is invalid: {exc}') from exc
    except Exception as exc:
        try:
            parsed_json = json.loads(cleaned_response_text)
            return GeneratedQuizSchema.model_validate(parsed_json)
        except Exception as inner_exc:
            raise QuizGenerationError('Generated quiz response could not be parsed.') from inner_exc


@transaction.atomic
def save_generated_quiz(user, canonical_video_url, generated_quiz):
    quiz = Quiz.objects.create(
        user=user,
        title=generated_quiz.title,
        description=generated_quiz.description,
        video_url=canonical_video_url,
    )

    questions = [
        Question(
            quiz=quiz,
            question_title=question.question_title,
            question_options=question.question_options,
            answer=question.answer,
        )
        for question in generated_quiz.questions
    ]

    Question.objects.bulk_create(questions)
    return quiz


def create_quiz_from_youtube_url(user, raw_url):
    video_id = extract_youtube_video_id(raw_url)
    canonical_video_url = build_canonical_youtube_url(video_id)

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = download_youtube_audio(canonical_video_url, temp_dir)
        transcript = transcribe_audio_file(audio_path)
        generated_quiz = generate_quiz_data_from_transcript(transcript)

    return save_generated_quiz(user, canonical_video_url, generated_quiz)