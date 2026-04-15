"""API views for registration, login, logout, and token refresh."""

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .authentication import CookieJWTAuthentication
from .serializers import RegistrationSerializer


def build_response(data, status_code):
    """Return a DRF response with the given payload and status."""
    return Response(data, status=status_code)


def delete_auth_cookies(response):
    """Remove authentication cookies from the response."""
    response.delete_cookie('access_token', path='/', samesite='Lax')
    response.delete_cookie('refresh_token', path='/', samesite='Lax')
    return response


def set_cookie_token(response, key, token):
    """Set a secure HttpOnly authentication cookie."""
    response.set_cookie(
        key=key,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        path='/',
    )


def set_auth_cookies(response, access_token, refresh_token):
    """Attach access and refresh cookies to the response."""
    set_cookie_token(response, 'access_token', access_token)
    set_cookie_token(response, 'refresh_token', refresh_token)
    return response


def get_refresh_token_from_cookies(request):
    """Return the refresh token from request cookies."""
    return request.COOKIES.get('refresh_token')


def build_login_payload(user):
    """Build the response payload for a successful login."""
    return {
        'detail': 'Login successfully!',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
    }


def build_logout_payload():
    """Build the response payload for a successful logout."""
    return {
        'detail': (
            'Log-Out successfully! All Tokens will be deleted. '
            'Refresh token is now invalid.'
        )
    }


def blacklist_refresh_token(refresh_token):
    """Blacklist a refresh token if it is valid."""
    if not refresh_token:
        return
    try:
        RefreshToken(refresh_token).blacklist()
    except (InvalidToken, TokenError):
        pass


def build_missing_refresh_response():
    """Return a response for a missing refresh token."""
    response = build_response(
        {'detail': 'Refresh token missing.'},
        status.HTTP_401_UNAUTHORIZED,
    )
    return delete_auth_cookies(response)


def build_invalid_refresh_response():
    """Return a response for an invalid refresh token."""
    response = build_response(
        {'detail': 'Invalid refresh token.'},
        status.HTTP_401_UNAUTHORIZED,
    )
    return delete_auth_cookies(response)


def build_internal_error_response():
    """Return a response for an unexpected refresh error."""
    response = build_response(
        {'detail': 'Internal server error.'},
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return delete_auth_cookies(response)


class RegistrationView(APIView):
    """Handle user registration."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Create a new user account."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return build_response(
            {'detail': 'User created successfully!'},
            status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """Handle logout and token invalidation."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Blacklist the refresh token and clear auth cookies."""
        refresh_token = get_refresh_token_from_cookies(request)
        blacklist_refresh_token(refresh_token)
        response = build_response(
            build_logout_payload(),
            status.HTTP_200_OK,
        )
        return delete_auth_cookies(response)


class CookieTokenObtainPairView(TokenObtainPairView):
    """Handle login and set JWT cookies."""

    permission_classes = [AllowAny]
    serializer_class = TokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """Validate credentials and return login response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = build_response(
            build_login_payload(serializer.user),
            status.HTTP_200_OK,
        )
        access_token = serializer.validated_data['access']
        refresh_token = serializer.validated_data['refresh']
        return set_auth_cookies(response, access_token, refresh_token)


class CookieTokenRefreshView(TokenRefreshView):
    """Refresh the access token from the refresh cookie."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Refresh the access token and update the access cookie."""
        refresh_token = get_refresh_token_from_cookies(request)
        if not refresh_token:
            return build_missing_refresh_response()
        return self.refresh_access_token(refresh_token)

    def refresh_access_token(self, refresh_token):
        """Validate the refresh token and return a refresh response."""
        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            return build_invalid_refresh_response()
        except Exception:
            return build_internal_error_response()
        return self.build_refresh_response(serializer.validated_data['access'])

    def build_refresh_response(self, access_token):
        """Return a successful refresh response with updated cookie."""
        response = build_response(
            {'detail': 'Token refreshed'},
            status.HTTP_200_OK,
        )
        set_cookie_token(response, 'access_token', access_token)
        return response