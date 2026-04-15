"""Serializers for user registration."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


def email_exists(email):
    """Return whether a user with the given email already exists."""
    return User.objects.filter(email__iexact=email).exists()


def passwords_match(password, confirmed_password):
    """Return whether both password fields contain the same value."""
    return password == confirmed_password


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate and create a new user account."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        """Serializer configuration for user registration."""

        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        """Ensure that the email address is unique."""
        if email_exists(value):
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate(self, attrs):
        """Ensure that both password fields match."""
        password = attrs['password']
        confirmed_password = attrs['confirmed_password']
        if not passwords_match(password, confirmed_password):
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        """Create a new user with the validated registration data."""
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)