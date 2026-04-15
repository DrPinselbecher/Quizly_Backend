"""Custom JWT authentication that reads the access token from cookies."""

from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate users with the JWT access token stored in cookies."""

    def authenticate(self, request):
        """Return the authenticated user and token from the access cookie."""
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        return user, validated_token