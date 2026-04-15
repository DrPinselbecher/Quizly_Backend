"""Tests for quiz service helpers and schema validation."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from pydantic import ValidationError as PydanticValidationError

from quiz_app.models import Quiz
from quiz_app.services import (
    GeneratedQuestionSchema,
    GeneratedQuizSchema,
    create_quiz_from_youtube_url,
    save_generated_quiz,
)
from quiz_app.utils import strip_markdown_code_fences

User = get_user_model()


class QuizServiceTests(TestCase):
    """Test quiz service functions and schema validation."""

    def setUp(self):
        """Create a user for service tests."""
        self.user = User.objects.create_user(
            username='rene',
            email='rene@example.com',
            password='StrongPass123!',
        )

    def create_generated_question(self, title='Question', answer='A'):
        """Create and return a valid generated question schema."""
        return GeneratedQuestionSchema(
            question_title=title,
            question_options=['A', 'B', 'C', 'D'],
            answer=answer,
        )

    def create_generated_quiz(self):
        """Create and return a valid generated quiz schema."""
        questions = [
            self.create_generated_question(title=f'Question {index}')
            for index in range(1, 11)
        ]
        return GeneratedQuizSchema(
            title='Python Quiz',
            description='A short description',
            questions=questions,
        )

    def test_strip_markdown_code_fences_removes_json_block_wrapping(self):
        value = '```json\n{"title": "Quiz"}\n```'
        result = strip_markdown_code_fences(value)
        self.assertEqual(result, '{"title": "Quiz"}')

    def test_save_generated_quiz_creates_quiz_and_questions(self):
        quiz = save_generated_quiz(
            user=self.user,
            canonical_video_url='https://www.youtube.com/watch?v=abc123XYZ',
            generated_quiz=self.create_generated_quiz(),
        )
        self.assertTrue(Quiz.objects.filter(id=quiz.id).exists())
        self.assertEqual(quiz.questions.count(), 10)
        self.assertEqual(quiz.video_url, 'https://www.youtube.com/watch?v=abc123XYZ')

    @patch('quiz_app.services.save_generated_quiz')
    @patch('quiz_app.services.generate_quiz_data_from_transcript')
    @patch('quiz_app.services.transcribe_audio_file')
    @patch('quiz_app.services.download_youtube_audio')
    @patch('quiz_app.services.build_canonical_youtube_url')
    @patch('quiz_app.services.extract_youtube_video_id')
    def test_create_quiz_from_youtube_url_calls_pipeline_in_order(
        self,
        mock_extract_video_id,
        mock_build_canonical_url,
        mock_download_audio,
        mock_transcribe_audio,
        mock_generate_quiz_data,
        mock_save_generated_quiz,
    ):
        self.configure_pipeline_mocks(
            mock_extract_video_id,
            mock_build_canonical_url,
            mock_download_audio,
            mock_transcribe_audio,
            mock_generate_quiz_data,
            mock_save_generated_quiz,
        )
        result = create_quiz_from_youtube_url(self.user, 'https://youtu.be/abc123XYZ')
        self.assertEqual(result, 'saved_quiz')
        self.assert_pipeline_calls(
            mock_extract_video_id,
            mock_build_canonical_url,
            mock_download_audio,
            mock_transcribe_audio,
            mock_generate_quiz_data,
            mock_save_generated_quiz,
        )

    def configure_pipeline_mocks(self, *mocks):
        """Configure mock return values for the quiz creation pipeline."""
        (
            mock_extract_video_id,
            mock_build_canonical_url,
            mock_download_audio,
            mock_transcribe_audio,
            mock_generate_quiz_data,
            mock_save_generated_quiz,
        ) = mocks
        mock_extract_video_id.return_value = 'abc123XYZ'
        mock_build_canonical_url.return_value = 'https://www.youtube.com/watch?v=abc123XYZ'
        mock_download_audio.return_value = '/tmp/audio.webm'
        mock_transcribe_audio.return_value = 'This is a transcript'
        mock_generate_quiz_data.return_value = 'generated_quiz_object'
        mock_save_generated_quiz.return_value = 'saved_quiz'

    def assert_pipeline_calls(self, *mocks):
        """Assert that each pipeline step was called with the correct data."""
        (
            mock_extract_video_id,
            mock_build_canonical_url,
            mock_download_audio,
            mock_transcribe_audio,
            mock_generate_quiz_data,
            mock_save_generated_quiz,
        ) = mocks
        mock_extract_video_id.assert_called_once_with('https://youtu.be/abc123XYZ')
        mock_build_canonical_url.assert_called_once_with('abc123XYZ')
        mock_download_audio.assert_called_once()
        mock_transcribe_audio.assert_called_once_with('/tmp/audio.webm')
        mock_generate_quiz_data.assert_called_once_with('This is a transcript')
        mock_save_generated_quiz.assert_called_once_with(
            self.user,
            'https://www.youtube.com/watch?v=abc123XYZ',
            'generated_quiz_object',
        )

    def test_generated_quiz_schema_rejects_wrong_number_of_questions(self):
        with self.assertRaises(PydanticValidationError):
            GeneratedQuizSchema(
                title='Python Quiz',
                description='A short description',
                questions=[self.create_generated_question()],
            )

    def test_generated_question_schema_rejects_answer_not_in_options(self):
        with self.assertRaises(PydanticValidationError):
            self.create_generated_question(answer='X')