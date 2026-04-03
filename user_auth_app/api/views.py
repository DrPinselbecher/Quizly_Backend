from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .authentication import CookieJWTAuthentication
from .serializers import RegistrationSerializer


class RegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "User created successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    authentication_classes = [CookieJWTAuthentication]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        response = Response(
            {
                "detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."
            },
            status=status.HTTP_200_OK
        )

        response.delete_cookie('access_token', path='/', samesite='Lax')
        response.delete_cookie('refresh_token', path='/', samesite='Lax')
        return response


class CookieTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=True,
                samesite='Lax'
            )
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite='Lax'
            )

            response.data = {
                "message": "Login successful. Tokens are set in HttpOnly cookies."
            }
        return response
    

class CookieTokenRefreshView(TokenRefreshView):
    def _clear_auth_cookies(self, response):
        response.delete_cookie('access_token', path='/', samesite='Lax')
        response.delete_cookie('refresh_token', path='/', samesite='Lax')
        return response

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            response = Response(
                {"detail": "Refresh token missing."},
                status=status.HTTP_401_UNAUTHORIZED
            )
            return self._clear_auth_cookies(response)

        serializer = self.get_serializer(data={"refresh": refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            response = Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_401_UNAUTHORIZED
            )
            return self._clear_auth_cookies(response)
        except Exception:
            response = Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return self._clear_auth_cookies(response)

        access_token = serializer.validated_data["access"]

        response = Response(
            {"detail": "Token refreshed"},
            status=status.HTTP_200_OK
        )
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=True,
            samesite='Lax',
            path='/'
        )
        return response
    