from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Request, Response

from app.config import get_settings
from app.models.schemas import AuthUser

COOKIE_NAME = "argus_session"
SEVEN_DAYS = timedelta(days=7)


def _cookie_kwargs() -> dict:
    settings = get_settings()
    return {
        "httponly": True,
        "secure": settings.is_production,
        "samesite": "none" if settings.is_production else "lax",
        "path": "/",
        "max_age": int(SEVEN_DAYS.total_seconds()),
    }


def sign_session(user: AuthUser) -> str:
    settings = get_settings()
    if not settings.session_secret:
        raise RuntimeError("SESSION_SECRET is not set")
    now = datetime.now(timezone.utc)
    payload = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "iat": int(now.timestamp()),
        "exp": int((now + SEVEN_DAYS).timestamp()),
    }
    return jwt.encode(payload, settings.session_secret, algorithm="HS256")


def read_session(request: Request) -> AuthUser | None:
    settings = get_settings()
    if not settings.session_secret:
        return None
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.session_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    user_id = payload.get("id")
    email = payload.get("email")
    if not user_id or not email:
        return None
    return AuthUser(
        id=str(user_id),
        email=str(email),
        name=str(payload.get("name") or str(email).split("@")[0]),
        picture=str(payload.get("picture") or ""),
    )


def set_session_cookie(response: Response, user: AuthUser) -> None:
    response.set_cookie(COOKIE_NAME, sign_session(user), **_cookie_kwargs())


def clear_session_cookie(response: Response) -> None:
    kwargs = _cookie_kwargs()
    response.delete_cookie(
        COOKIE_NAME,
        path=kwargs["path"],
        httponly=kwargs["httponly"],
        secure=kwargs["secure"],
        samesite=kwargs["samesite"],
    )
