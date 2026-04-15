"""Tests for custom quiz permissions."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from quiz_app.models import Quiz
from quiz_app.permissions import IsQuizOwner

User = get_user_model()


class IsQuizOwnerPermissionTests(TestCase):
    """Test object-level ownership permission for quizzes."""

    def setUp(self):
        """Create test users, permission instance, and sample quiz."""
        self.factory = APIRequestFactory()
        self.permission = IsQuizOwner()
        self.owner = self.create_user('owner', 'owner@example.com')
        self.other_user = self.create_user('other', 'other@example.com')
        self.quiz = self.create_quiz(self.owner)

    def create_user(self, username, email):
        """Create and return a user for permission tests."""
        return User.objects.create_user(
            username=username,
            email=email,
            password='StrongPass123!',
        )

    def create_quiz(self, user):
        """Create and return a quiz for the given user."""
        return Quiz.objects.create(
            user=user,
            title='Python Quiz',
            description='A short description',
            video_url='https://www.youtube.com/watch?v=abc123XYZ',
        )

    def build_request(self, user):
        """Create a request and attach the given user."""
        request = self.factory.get('/api/quizzes/1/')
        request.user = user
        return request

    def test_permission_allows_owner(self):
        request = self.build_request(self.owner)
        is_allowed = self.permission.has_object_permission(
            request,
            None,
            self.quiz,
        )
        self.assertTrue(is_allowed)

    def test_permission_denies_non_owner(self):
        request = self.build_request(self.other_user)
        is_allowed = self.permission.has_object_permission(
            request,
            None,
            self.quiz,
        )
        self.assertFalse(is_allowed)