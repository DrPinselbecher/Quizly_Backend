"""Tests for quiz API views."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from quiz_app.models import Question, Quiz

User = get_user_model()


class QuizViewTests(APITestCase):
    """Test quiz list, detail, update, and delete endpoints."""

    def setUp(self):
        """Create users, quizzes, questions, and endpoint URLs."""
        self.user = self.create_user('rene', 'rene@example.com')
        self.other_user = self.create_user('other', 'other@example.com')
        self.quiz = self.create_quiz(self.user, 'Python Quiz')
        self.other_quiz = self.create_quiz(self.other_user, 'Other Quiz')
        self.create_question(self.quiz, 'What is Python?', 'Language')
        self.create_question(self.other_quiz, 'Other question?', 'A')
        self.list_create_url = reverse('quiz-list-create')
        self.detail_url = reverse('quiz-detail', kwargs={'pk': self.quiz.id})
        self.other_detail_url = reverse(
            'quiz-detail',
            kwargs={'pk': self.other_quiz.id},
        )

    def create_user(self, username, email):
        """Create and return a user for view tests."""
        return User.objects.create_user(
            username=username,
            email=email,
            password='StrongPass123!',
        )

    def create_quiz(self, user, title):
        """Create and return a quiz for the given user."""
        return Quiz.objects.create(
            user=user,
            title=title,
            description='A short description',
            video_url='https://www.youtube.com/watch?v=abc123XYZ',
        )

    def create_question(self, quiz, title, answer):
        """Create and return a question for the given quiz."""
        return Question.objects.create(
            quiz=quiz,
            question_title=title,
            question_options=['Language', 'Animal', 'Game', 'Tool'],
            answer=answer,
        )

    def authenticate(self):
        """Authenticate the API client as the main test user."""
        self.client.force_authenticate(user=self.user)

    def test_get_quizzes_returns_only_current_users_quizzes(self):
        self.authenticate()
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.quiz.id)
        self.assertEqual(response.data[0]['title'], 'Python Quiz')

    @patch('quiz_app.api.views.create_quiz_from_youtube_url')
    def test_post_quiz_success(self, mock_create_quiz):
        self.authenticate()
        created_quiz = self.create_created_quiz()
        mock_create_quiz.return_value = created_quiz
        response = self.post_quiz('https://youtu.be/new123XYZ')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Created Quiz')
        self.assertEqual(
            response.data['video_url'],
            'https://www.youtube.com/watch?v=new123XYZ',
        )
        mock_create_quiz.assert_called_once()

    def create_created_quiz(self):
        """Create and return a quiz used for mocked creation tests."""
        quiz = Quiz.objects.create(
            user=self.user,
            title='Created Quiz',
            description='Created description',
            video_url='https://www.youtube.com/watch?v=new123XYZ',
        )
        self.create_created_question(quiz)
        return quiz

    def create_created_question(self, quiz):
        """Create a sample question for a mocked created quiz."""
        Question.objects.create(
            quiz=quiz,
            question_title='Created question?',
            question_options=['A', 'B', 'C', 'D'],
            answer='A',
        )

    def post_quiz(self, url):
        """Send a POST request to create a quiz."""
        return self.client.post(
            self.list_create_url,
            {'url': url},
            format='json',
        )

    def test_post_quiz_returns_400_for_invalid_url(self):
        self.authenticate()
        response = self.post_quiz('https://example.com/video')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)

    def test_get_quiz_detail_returns_own_quiz(self):
        self.authenticate()
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.quiz.id)
        self.assertEqual(response.data['title'], 'Python Quiz')

    def test_get_quiz_detail_returns_403_for_foreign_quiz(self):
        self.authenticate()
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_quiz_updates_own_quiz(self):
        self.authenticate()
        response = self.patch_quiz(self.detail_url, 'Updated Title')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, 'Updated Title')

    def patch_quiz(self, url, title):
        """Send a PATCH request to update a quiz title."""
        return self.client.patch(
            url,
            {'title': title},
            format='json',
        )

    def test_patch_quiz_returns_403_for_foreign_quiz(self):
        self.authenticate()
        response = self.patch_quiz(self.other_detail_url, 'Updated Title')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_quiz_deletes_own_quiz(self):
        self.authenticate()
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(id=self.quiz.id).exists())

    def test_delete_quiz_returns_403_for_foreign_quiz(self):
        self.authenticate()
        response = self.client.delete(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_quiz_endpoints_require_authentication(self):
        list_response = self.client.get(self.list_create_url)
        detail_response = self.client.get(self.detail_url)
        self.assertEqual(list_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(detail_response.status_code, status.HTTP_401_UNAUTHORIZED)