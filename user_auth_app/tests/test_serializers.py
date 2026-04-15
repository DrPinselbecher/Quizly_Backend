"""Tests for the registration serializer."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from user_auth_app.api.serializers import RegistrationSerializer

User = get_user_model()

PASSWORD_CONFIRM_FIELD = 'confirmed_password'


class RegistrationSerializerTests(TestCase):
    """Test registration serializer validation and user creation."""

    def build_data(self, **overrides):
        data = {
            'username': 'rene',
            'email': 'rene@example.com',
            'password': 'StrongPass123!',
            PASSWORD_CONFIRM_FIELD: 'StrongPass123!',
        }
        data.update(overrides)
        return data

    def test_serializer_with_valid_data_creates_user(self):
        serializer = RegistrationSerializer(data=self.build_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.username, 'rene')
        self.assertEqual(user.email, 'rene@example.com')
        self.assertTrue(user.check_password('StrongPass123!'))

    def test_serializer_rejects_password_mismatch(self):
        serializer = RegistrationSerializer(
            data=self.build_data(confirmed_password='WrongPass123!'),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn(PASSWORD_CONFIRM_FIELD, serializer.errors)

    def test_serializer_rejects_duplicate_email(self):
        User.objects.create_user(
            username='existing_user',
            email='rene@example.com',
            password='StrongPass123!',
        )
        serializer = RegistrationSerializer(
            data=self.build_data(username='new_user'),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)