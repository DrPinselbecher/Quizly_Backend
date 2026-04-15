"""Serializers for quiz API input and output."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from quiz_app.models import Question, Quiz
from quiz_app.utils import build_canonical_youtube_url, extract_youtube_video_id


class QuestionSerializer(serializers.ModelSerializer):
    """Serialize question data for read-only API responses."""

    class Meta:
        """Serializer configuration for Question."""

        model = Question
        fields = [
            'id',
            'question_title',
            'question_options',
            'answer',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class QuizSerializer(serializers.ModelSerializer):
    """Serialize quiz data with nested questions for read-only responses."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        """Serializer configuration for Quiz."""

        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]
        read_only_fields = fields


class QuizCreateSerializer(serializers.Serializer):
    """Validate input data for quiz creation requests."""

    url = serializers.URLField()

    def validate_url(self, value):
        """Validate and normalize a YouTube URL."""
        try:
            video_id = extract_youtube_video_id(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError('Invalid YouTube URL.') from exc
        return build_canonical_youtube_url(video_id)


class QuizUpdateSerializer(serializers.ModelSerializer):
    """Validate editable quiz fields for partial updates."""

    class Meta:
        """Serializer configuration for quiz updates."""

        model = Quiz
        fields = ['title', 'description']

    def validate_title(self, value):
        """Validate and clean the quiz title."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise serializers.ValidationError('Title cannot be empty.')
        return cleaned_value

    def validate_description(self, value):
        """Validate and clean the quiz description."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise serializers.ValidationError('Description cannot be empty.')
        if len(cleaned_value) > 150:
            raise serializers.ValidationError(
                'Description must not exceed 150 characters.'
            )
        return cleaned_value