"""API views for quiz list, creation, detail, update, and deletion."""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.models import Quiz
from quiz_app.permissions import IsQuizOwner
from quiz_app.services import QuizGenerationError, create_quiz_from_youtube_url

from .serializers import QuizCreateSerializer, QuizSerializer, QuizUpdateSerializer


class QuizListCreateView(generics.GenericAPIView):
    """Handle listing quizzes and creating a new quiz."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return quizzes that belong to the authenticated user."""
        return Quiz.objects.filter(user=self.request.user).prefetch_related(
            'questions'
        )

    def get(self, request, *args, **kwargs):
        """Return all quizzes of the authenticated user."""
        quizzes = self.get_queryset()
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """Create a new quiz from a YouTube URL."""
        serializer = self._validate_create_request(request.data)
        return self._create_quiz_response(request.user, serializer.validated_data)

    def _validate_create_request(self, data):
        """Validate incoming data for quiz creation."""
        serializer = QuizCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def _create_quiz_response(self, user, validated_data):
        """Create a quiz and return the appropriate API response."""
        try:
            quiz = self._generate_quiz(user, validated_data['url'])
        except QuizGenerationError as exc:
            return self._build_error_response(exc)
        return self._build_created_response(quiz)

    def _generate_quiz(self, user, raw_url):
        """Generate and save a quiz from the provided YouTube URL."""
        return create_quiz_from_youtube_url(user=user, raw_url=raw_url)

    def _build_created_response(self, quiz):
        """Return the serialized response for a newly created quiz."""
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _build_error_response(self, exc):
        """Return a standardized error response for quiz generation."""
        return Response(
            {'detail': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class QuizDetailView(generics.GenericAPIView):
    """Handle retrieve, partial update, and deletion of a quiz."""

    permission_classes = [IsAuthenticated, IsQuizOwner]
    queryset = Quiz.objects.all().prefetch_related('questions')

    def get_object(self):
        """Return the requested quiz and enforce object permissions."""
        quiz = generics.get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, quiz)
        return quiz

    def get(self, request, *args, **kwargs):
        """Return the details of a single quiz."""
        quiz = self.get_object()
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        """Partially update title or description of a quiz."""
        quiz = self.get_object()
        self._update_quiz(quiz, request.data)
        return self._build_detail_response(quiz)

    def delete(self, request, *args, **kwargs):
        """Delete the requested quiz."""
        quiz = self.get_object()
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _update_quiz(self, quiz, data):
        """Validate and save partial quiz updates."""
        serializer = QuizUpdateSerializer(quiz, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def _build_detail_response(self, quiz):
        """Return the serialized response for a single quiz."""
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)