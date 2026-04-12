from rest_framework import serializers

from quiz_app.models import Quiz, Question, extract_youtube_video_id, build_canonical_youtube_url


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
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
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
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
    url = serializers.URLField()

    def validate_url(self, value):
        try:
            video_id = extract_youtube_video_id(value)
            return build_canonical_youtube_url(video_id)
        except Exception:
            raise serializers.ValidationError('Invalid YouTube URL.')


class QuizUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['title', 'description']

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Title cannot be empty.')
        return value

    def validate_description(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Description cannot be empty.')
        if len(value) > 150:
            raise serializers.ValidationError('Description must not exceed 150 characters.')
        return value