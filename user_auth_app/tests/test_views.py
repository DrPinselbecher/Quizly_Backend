"""Tests for authentication API views."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

PASSWORD_CONFIRM_FIELD = 'confirmed_password'


class AuthViewTests(APITestCase):
    """Test registration, login, logout, and token refresh endpoints."""

    def setUp(self):
        self.register_url = reverse('registration')
        self.login_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')
        self.logout_url = reverse('logout')
        self.user = User.objects.create_user(
            username='rene',
            email='rene@example.com',
            password='StrongPass123!',
        )

    def build_register_data(self, **overrides):
        data = {
            'username': 'new_user',
            'email': 'new_user@example.com',
            'password': 'StrongPass123!',
            PASSWORD_CONFIRM_FIELD: 'StrongPass123!',
        }
        data.update(overrides)
        return data

    def build_login_data(self, password='StrongPass123!'):
        return {
            'username': 'rene',
            'password': password,
        }

    def post_json(self, url, data=None):
        return self.client.post(url, data or {}, format='json')

    def set_refresh_cookie(self, token):
        self.client.cookies['refresh_token'] = token

    def set_auth_cookies(self, access_token, refresh_token):
        self.client.cookies['access_token'] = access_token
        self.client.cookies['refresh_token'] = refresh_token

    def create_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        return str(refresh.access_token), str(refresh)

    def test_register_success(self):
        response = self.post_json(self.register_url, self.build_register_data())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['detail'], 'User created successfully!')
        self.assertTrue(User.objects.filter(username='new_user').exists())

    def test_register_returns_400_for_password_mismatch(self):
        data = self.build_register_data(confirmed_password='WrongPass123!')
        response = self.post_json(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(PASSWORD_CONFIRM_FIELD, response.data)

    def test_login_success_returns_user_and_sets_cookies(self):
        response = self.post_json(self.login_url, self.build_login_data())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Login successfully!')
        self.assertEqual(response.data['user']['username'], 'rene')
        self.assertEqual(response.data['user']['email'], 'rene@example.com')
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_login_returns_401_for_invalid_credentials(self):
        response = self.post_json(
            self.login_url,
            self.build_login_data(password='WrongPassword123!'),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_success_with_refresh_cookie(self):
        _, refresh_token = self.create_tokens()
        self.set_refresh_cookie(refresh_token)
        response = self.post_json(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        self.assertIn('access_token', response.cookies)

    def test_refresh_returns_401_when_refresh_cookie_is_missing(self):
        response = self.post_json(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Refresh token missing.')

    def test_logout_success_deletes_cookies_for_authenticated_user(self):
        access_token, refresh_token = self.create_tokens()
        self.set_auth_cookies(access_token, refresh_token)
        response = self.post_json(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['detail'],
            'Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid.',
        )
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_logout_returns_401_when_user_is_not_authenticated(self):
        response = self.post_json(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)