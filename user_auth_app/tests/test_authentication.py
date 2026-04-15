"""Tests for cookie-based JWT authentication."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from user_auth_app.api.authentication import CookieJWTAuthentication

User = get_user_model()


class CookieJWTAuthenticationTests(TestCase):
    """Test authentication with JWT access tokens stored in cookies."""

    def setUp(self):
        self.factory = RequestFactory()
        self.authentication = CookieJWTAuthentication()
        self.user = User.objects.create_user(
            username='rene',
            email='rene@example.com',
            password='StrongPass123!',
        )

    def build_request(self):
        return self.factory.get('/api/quizzes/')

    def set_access_cookie(self, request, token):
        request.COOKIES['access_token'] = token

    def create_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        return str(refresh.access_token)

    def test_authenticate_returns_user_and_token_when_cookie_is_valid(self):
        request = self.build_request()
        self.set_access_cookie(request, self.create_access_token())
        result = self.authentication.authenticate(request)
        self.assertIsNotNone(result)
        authenticated_user, validated_token = result
        self.assertEqual(authenticated_user.id, self.user.id)
        self.assertIsNotNone(validated_token)

    def test_authenticate_returns_none_when_cookie_is_missing(self):
        request = self.build_request()
        result = self.authentication.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_raises_invalid_token_for_bad_cookie(self):
        request = self.build_request()
        self.set_access_cookie(request, 'invalid.token.value')
        with self.assertRaises(InvalidToken):
            self.authentication.authenticate(request)