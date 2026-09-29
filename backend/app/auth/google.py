from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import get_settings
from app.errors import ApiError
from app.logging_config import get_logger
from app.models.schemas import AuthUser

logger = get_logger(__name__)


def is_auth_configured() -> bool:
    return get_settings().auth_configured


def verify_google_id_token(credential: str) -> AuthUser:
    settings = get_settings()
    if not settings.google_client_id:
        raise ApiError(503, "GOOGLE_CLIENT_ID is not set", code="AUTH_NOT_CONFIGURED")

    try:
        payload = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception as exc:
        logger.error("Google token verification failed: %s", exc)
        raise ApiError(401, "Google sign-in failed. Try again.", code="INVALID_TOKEN") from exc

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise ApiError(401, "Google token was missing identity claims", code="INVALID_TOKEN")
    if payload.get("email_verified") is False:
        raise ApiError(401, "Google email is not verified", code="INVALID_TOKEN")

    return AuthUser(
        id=str(sub),
        email=str(email),
        name=str(payload.get("name") or str(email).split("@")[0]),
        picture=str(payload.get("picture") or ""),
    )
