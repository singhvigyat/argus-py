from fastapi import APIRouter, Request, Response

from app.auth.deps import get_optional_user
from app.auth.google import is_auth_configured, verify_google_id_token
from app.auth.session import clear_session_cookie, set_session_cookie
from app.auth.usage import get_limits, get_quota
from app.config import get_settings
from app.db.logins import record_login
from app.db.mongo import mongo_available
from app.db.users import find_by_id, upsert_from_google
from app.errors import ApiError
from app.models.schemas import AuthConfig, AuthResponse, GoogleLoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfig)
async def get_auth_config() -> AuthConfig:
    daily, global_limit = get_limits()
    settings = get_settings()
    return AuthConfig(
        googleClientId=settings.google_client_id,
        configured=is_auth_configured(),
        dailyLimit=daily,
        globalDailyLimit=global_limit,
    )


@router.get("/me", response_model=AuthResponse)
async def get_me(request: Request, response: Response) -> AuthResponse:
    user = get_optional_user(request)
    if not user:
        raise ApiError(401, "Not signed in", code="UNAUTHENTICATED")
    if mongo_available():
        db_user = await find_by_id(user.id)
        if not db_user:
            clear_session_cookie(response)
            raise ApiError(401, "Not signed in", code="UNAUTHENTICATED")
        user = db_user
    return AuthResponse(user=user, quota=await get_quota(user.id))


@router.post("/google", response_model=AuthResponse)
async def login_with_google(body: GoogleLoginRequest, request: Request, response: Response) -> AuthResponse:
    if not is_auth_configured():
        raise ApiError(
            503,
            "Google sign-in is not configured. Set GOOGLE_CLIENT_ID and SESSION_SECRET.",
            code="AUTH_NOT_CONFIGURED",
        )
    if not body.credential.strip():
        raise ApiError(400, "Google credential is required")

    user = verify_google_id_token(body.credential)
    if mongo_available():
        user = await upsert_from_google(user)
        await record_login(user, request)
    set_session_cookie(response, user)
    return AuthResponse(user=user, quota=await get_quota(user.id))


@router.post("/logout")
async def logout(response: Response) -> dict:
    clear_session_cookie(response)
    return {"ok": True}
