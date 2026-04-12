from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.models import Quiz
from quiz_app.permissions import IsQuizOwner
from quiz_app.services import QuizGenerationError, create_quiz_from_youtube_url
from .serializers import QuizSerializer, QuizCreateSerializer, QuizUpdateSerializer


class QuizListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(user=self.request.user).prefetch_related('questions')

    def get(self, request, *args, **kwargs):
        quizzes = self.get_queryset()
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        create_serializer = QuizCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        try:
            quiz = create_quiz_from_youtube_url(
                user=request.user,
                raw_url=create_serializer.validated_data['url']
            )
        except QuizGenerationError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizDetailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsQuizOwner]
    queryset = Quiz.objects.all().prefetch_related('questions')

    def get_object(self):
        obj = generics.get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        quiz = self.get_object()
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        quiz = self.get_object()
        serializer = QuizUpdateSerializer(quiz, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = QuizSerializer(quiz)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        quiz = self.get_object()
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)