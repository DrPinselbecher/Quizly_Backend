"""Admin configuration for quiz and question models."""

from django.contrib import admin

from quiz_app.models import Question, Quiz


class QuestionInline(admin.TabularInline):
    """Display quiz questions inline inside the quiz admin view."""

    model = Question
    extra = 0
    fields = (
        'question_title',
        'question_options',
        'answer',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin configuration for quizzes."""

    list_display = (
        'id',
        'title',
        'user',
        'video_url',
        'created_at',
        'updated_at',
    )
    search_fields = ('title', 'description', 'user__username', 'user__email')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin configuration for quiz questions."""

    list_display = (
        'id',
        'quiz',
        'question_title',
        'answer',
        'created_at',
        'updated_at',
    )
    search_fields = ('question_title', 'answer', 'quiz__title')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')