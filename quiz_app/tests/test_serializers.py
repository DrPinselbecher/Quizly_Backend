"""Tests for quiz models and YouTube URL helper functions."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from quiz_app.models import Question, Quiz
from quiz_app.utils import build_canonical_youtube_url, extract_youtube_video_id

User = get_user_model()


class QuizModelTests(TestCase):
    """Test quiz and question model behavior."""

    def setUp(self):
        """Create a user for model tests."""
        self.user = User.objects.create_user(
            username='rene',
            email='rene@example.com',
            password='StrongPass123!',
        )

    def create_quiz(self, video_url='https://www.youtube.com/watch?v=abc123XYZ'):
        """Create and return a valid quiz instance."""
        return Quiz.objects.create(
            user=self.user,
            title='Python Quiz',
            description='A short description',
            video_url=video_url,
        )

    def create_question(self, **kwargs):
        """Create and return a question instance."""
        defaults = {
            'quiz': self.create_quiz(),
            'question_title': 'What is Python?',
            'question_options': ['Language', 'Animal', 'Game', 'Tool'],
            'answer': 'Language',
        }
        defaults.update(kwargs)
        return Question(**defaults)

    def test_extract_youtube_video_id_from_watch_url(self):
        url = 'https://www.youtube.com/watch?v=abc123XYZ'
        self.assertEqual(extract_youtube_video_id(url), 'abc123XYZ')

    def test_extract_youtube_video_id_from_short_url(self):
        url = 'https://youtu.be/abc123XYZ'
        self.assertEqual(extract_youtube_video_id(url), 'abc123XYZ')

    def test_extract_youtube_video_id_from_shorts_url(self):
        url = 'https://www.youtube.com/shorts/abc123XYZ'
        self.assertEqual(extract_youtube_video_id(url), 'abc123XYZ')

    def test_extract_youtube_video_id_from_embed_url(self):
        url = 'https://www.youtube.com/embed/abc123XYZ'
        self.assertEqual(extract_youtube_video_id(url), 'abc123XYZ')

    def test_extract_youtube_video_id_raises_for_invalid_url(self):
        with self.assertRaises(ValidationError):
            extract_youtube_video_id('https://example.com/video')

    def test_build_canonical_youtube_url(self):
        expected_url = 'https://www.youtube.com/watch?v=abc123XYZ'
        self.assertEqual(build_canonical_youtube_url('abc123XYZ'), expected_url)

    def test_quiz_save_normalizes_video_url(self):
        quiz = self.create_quiz(video_url='https://youtu.be/abc123XYZ')
        expected_url = 'https://www.youtube.com/watch?v=abc123XYZ'
        self.assertEqual(quiz.video_url, expected_url)

    def test_question_save_with_valid_data(self):
        question = self.create_question()
        question.save()
        self.assertEqual(question.answer, 'Language')
        self.assertEqual(len(question.question_options), 4)

    def test_question_raises_when_options_are_not_exactly_four(self):
        question = self.create_question(
            question_options=['Language', 'Animal', 'Game'],
        )
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_question_raises_when_options_are_not_unique(self):
        question = self.create_question(
            question_options=['Language', 'Language', 'Game', 'Tool'],
        )
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_question_raises_when_answer_is_not_in_options(self):
        question = self.create_question(answer='Framework')
        with self.assertRaises(ValidationError):
            question.full_clean()