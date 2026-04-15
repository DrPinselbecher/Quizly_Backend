from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from quiz_app.utils import build_canonical_youtube_url, extract_youtube_video_id


class Quiz(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quizzes'
    )
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=150)
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def clean(self):
        video_id = extract_youtube_video_id(self.video_url)
        self.video_url = build_canonical_youtube_url(video_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_title = models.CharField(max_length=255)
    question_options = models.JSONField()
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def clean(self):
        if not isinstance(self.question_options, list):
            raise ValidationError({'question_options': 'question_options must be a list.'})

        if len(self.question_options) != 4:
            raise ValidationError({'question_options': 'Each question must have exactly 4 options.'})

        if len(set(self.question_options)) != 4:
            raise ValidationError({'question_options': 'Each option must be unique.'})

        if self.answer not in self.question_options:
            raise ValidationError({'answer': 'Answer must be one of the question options.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.question_title