"""Service layer for generating quizzes from YouTube videos."""

import json
import tempfile
from functools import lru_cache
from pathlib import Path

import whisper
from django.conf import settings
from django.db import transaction
from google import genai
from pydantic import (
    BaseModel,
    Field,
    ValidationError as PydanticValidationError,
    field_validator,
    model_validator,
)
from yt_dlp import YoutubeDL

from quiz_app.models import Question, Quiz
from quiz_app.utils import (
    build_canonical_youtube_url,
    build_quiz_prompt,
    extract_youtube_video_id,
    strip_markdown_code_fences,
)


class QuizGenerationError(Exception):
    """Raised when quiz generation fails at any service step."""


def clean_required_text(value, field_name, max_length=None):
    """Trim text and ensure that it is not empty."""
    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError(f'{field_name} must not be empty.')
    if max_length and len(cleaned_value) > max_length:
        raise ValueError(f'{field_name} must not exceed {max_length} characters.')
    return cleaned_value


def validate_options_list(options):
    """Validate that a question has four unique and non-empty options."""
    cleaned_options = [option.strip() for option in options]
    if len(cleaned_options) != 4:
        raise ValueError('Each question must have exactly 4 options.')
    if len(set(cleaned_options)) != 4:
        raise ValueError('Each question option must be unique.')
    if any(not option for option in cleaned_options):
        raise ValueError('Question options must not be empty.')
    return cleaned_options


def validate_question_count(questions):
    """Ensure that the generated quiz contains exactly ten questions."""
    if len(questions) != 10:
        raise ValueError('Exactly 10 questions are required.')
    return questions


def get_setting_value(name, default=None):
    """Return a value from Django settings with an optional default."""
    return getattr(settings, name, default)


class GeneratedQuestionSchema(BaseModel):
    """Schema for a single generated quiz question."""

    question_title: str = Field(min_length=1, max_length=255)
    question_options: list[str]
    answer: str = Field(min_length=1, max_length=255)

    @field_validator('question_options')
    @classmethod
    def validate_question_options(cls, value):
        """Validate the list of answer options."""
        return validate_options_list(value)

    @field_validator('question_title')
    @classmethod
    def validate_question_title(cls, value):
        """Validate the generated question title."""
        return clean_required_text(value, 'Question title', 255)

    @field_validator('answer')
    @classmethod
    def validate_answer(cls, value):
        """Validate the generated correct answer."""
        return clean_required_text(value, 'Answer', 255)

    @model_validator(mode='after')
    def validate_answer_in_options(self):
        """Ensure that the answer exists inside the provided options."""
        if self.answer not in self.question_options:
            raise ValueError('Answer must be one of the question options.')
        return self


class GeneratedQuizSchema(BaseModel):
    """Schema for the full generated quiz payload."""

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=150)
    questions: list[GeneratedQuestionSchema]

    @field_validator('title')
    @classmethod
    def validate_title(cls, value):
        """Validate the generated quiz title."""
        return clean_required_text(value, 'Title', 255)

    @field_validator('description')
    @classmethod
    def validate_description(cls, value):
        """Validate the generated quiz description."""
        return clean_required_text(value, 'Description', 150)

    @field_validator('questions')
    @classmethod
    def validate_questions(cls, value):
        """Validate the number of generated questions."""
        return validate_question_count(value)


@lru_cache(maxsize=1)
def get_whisper_model():
    """Load and cache the configured Whisper model."""
    model_name = get_setting_value('WHISPER_MODEL', 'base')
    return whisper.load_model(model_name)


def build_output_template(output_dir):
    """Build the output file pattern for yt-dlp downloads."""
    return str(Path(output_dir) / 'audio.%(ext)s')


def build_youtube_download_options(output_dir):
    """Return yt-dlp options for audio-only downloads."""
    return {
        'format': 'bestaudio/best',
        'outtmpl': build_output_template(output_dir),
        'quiet': True,
        'noplaylist': True,
    }


def find_downloaded_audio_file(output_dir):
    """Return the path of the downloaded audio file."""
    audio_files = sorted(Path(output_dir).glob('audio.*'))
    if not audio_files:
        raise QuizGenerationError('No audio file was downloaded.')
    return str(audio_files[0])


def download_youtube_audio(video_url, output_dir):
    """Download the audio track of a YouTube video."""
    options = build_youtube_download_options(output_dir)
    try:
        with YoutubeDL(options) as ydl:
            ydl.download([video_url])
    except Exception as exc:
        raise QuizGenerationError('Could not download the YouTube audio.') from exc
    return find_downloaded_audio_file(output_dir)


def get_transcript_text(result):
    """Extract and validate transcript text from Whisper output."""
    transcript = result.get('text', '').strip()
    if not transcript:
        raise QuizGenerationError('Transcript is empty.')
    return transcript


def transcribe_audio_file(audio_path):
    """Transcribe an audio file with Whisper."""
    try:
        result = get_whisper_model().transcribe(audio_path)
    except Exception as exc:
        raise QuizGenerationError('Could not transcribe the audio file.') from exc
    return get_transcript_text(result)


def get_gemini_api_key():
    """Return the Gemini API key or raise an error if missing."""
    api_key = get_setting_value('GEMINI_API_KEY')
    if not api_key:
        raise QuizGenerationError('GEMINI_API_KEY is missing.')
    return api_key


def build_generation_config():
    """Return the Gemini generation config for structured JSON output."""
    return {
        'response_mime_type': 'application/json',
        'response_json_schema': GeneratedQuizSchema.model_json_schema(),
    }


def request_gemini_quiz(prompt):
    """Send the transcript prompt to Gemini and return the raw response."""
    client = genai.Client(api_key=get_gemini_api_key())
    model_name = get_setting_value('GEMINI_MODEL', 'gemini-2.5-flash')
    return client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=build_generation_config(),
    )


def get_response_text(response):
    """Extract response text and ensure it is not empty."""
    response_text = getattr(response, 'text', '') or ''
    if not response_text.strip():
        raise QuizGenerationError('Gemini returned an empty response.')
    return response_text


def validate_generated_quiz_json(cleaned_response_text):
    """Validate a JSON string directly against the quiz schema."""
    return GeneratedQuizSchema.model_validate_json(cleaned_response_text)


def validate_generated_quiz_dict(cleaned_response_text):
    """Parse JSON manually and validate it as a Python dictionary."""
    parsed_json = json.loads(cleaned_response_text)
    return GeneratedQuizSchema.model_validate(parsed_json)


def parse_generated_quiz(cleaned_response_text):
    """Parse and validate the generated quiz response."""
    try:
        return validate_generated_quiz_json(cleaned_response_text)
    except PydanticValidationError as exc:
        raise QuizGenerationError(f'Generated quiz data is invalid: {exc}') from exc
    except Exception as exc:
        try:
            return validate_generated_quiz_dict(cleaned_response_text)
        except Exception as inner_exc:
            raise QuizGenerationError(
                'Generated quiz response could not be parsed.'
            ) from inner_exc


def generate_quiz_data_from_transcript(transcript):
    """Generate structured quiz data from a transcript."""
    prompt = build_quiz_prompt(transcript)
    try:
        response = request_gemini_quiz(prompt)
    except Exception as exc:
        raise QuizGenerationError(
            'Could not generate quiz content with Gemini.'
        ) from exc
    response_text = get_response_text(response)
    cleaned_text = strip_markdown_code_fences(response_text)
    return parse_generated_quiz(cleaned_text)


def build_question_instances(quiz, generated_quiz):
    """Build unsaved question instances for bulk creation."""
    return [
        Question(
            quiz=quiz,
            question_title=question.question_title,
            question_options=question.question_options,
            answer=question.answer,
        )
        for question in generated_quiz.questions
    ]


@transaction.atomic
def save_generated_quiz(user, canonical_video_url, generated_quiz):
    """Save a generated quiz and all related questions."""
    quiz = Quiz.objects.create(
        user=user,
        title=generated_quiz.title,
        description=generated_quiz.description,
        video_url=canonical_video_url,
    )
    questions = build_question_instances(quiz, generated_quiz)
    Question.objects.bulk_create(questions)
    return quiz


def build_canonical_video_url(raw_url):
    """Extract the video ID and return the canonical YouTube URL."""
    video_id = extract_youtube_video_id(raw_url)
    return build_canonical_youtube_url(video_id)


def generate_quiz_from_video_url(video_url):
    """Download, transcribe, and generate quiz data for a video URL."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = download_youtube_audio(video_url, temp_dir)
        transcript = transcribe_audio_file(audio_path)
        return generate_quiz_data_from_transcript(transcript)


def create_quiz_from_youtube_url(user, raw_url):
    """Create and persist a quiz from a YouTube URL."""
    canonical_video_url = build_canonical_video_url(raw_url)
    generated_quiz = generate_quiz_from_video_url(canonical_video_url)
    return save_generated_quiz(user, canonical_video_url, generated_quiz)