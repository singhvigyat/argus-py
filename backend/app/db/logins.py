from fastapi import Request

from app.db.mongo import get_db
from app.db.util import utc_now
from app.models.schemas import AuthUser


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return request.client.host
    return ""


async def record_login(user: AuthUser, request: Request) -> None:
    db = get_db()
    if db is None:
        return
    agent = (request.headers.get("user-agent") or "")[:512]
    await db.login_events.insert_one(
        {
            "userId": user.id,
            "email": user.email,
            "ip": client_ip(request),
            "userAgent": agent,
            "createdAt": utc_now(),
        }
    )
