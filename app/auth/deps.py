from fastapi import Request

from app.auth.google import is_auth_configured
from app.auth.session import read_session
from app.errors import ApiError
from app.models.schemas import AuthUser


def get_optional_user(request: Request) -> AuthUser | None:
    return read_session(request)


def require_user(request: Request) -> AuthUser:
    if not is_auth_configured():
        raise ApiError(
            503,
            "Google sign-in is not configured on the server.",
            code="AUTH_NOT_CONFIGURED",
        )
    user = read_session(request)
    if not user:
        raise ApiError(
            401,
            "Sign in with Google to run a reading.",
            code="UNAUTHENTICATED",
        )
    return user
