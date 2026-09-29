from app.db.mongo import get_db
from app.db.util import utc_now
from app.models.schemas import AuthUser


def _to_user(doc: dict) -> AuthUser:
    return AuthUser(
        id=str(doc["_id"]),
        email=str(doc.get("email") or ""),
        name=str(doc.get("name") or str(doc.get("email") or "").split("@")[0]),
        picture=str(doc.get("picture") or ""),
    )


async def upsert_from_google(user: AuthUser) -> AuthUser:
    db = get_db()
    if db is None:
        return user
    now = utc_now()
    await db.users.update_one(
        {"_id": user.id},
        {
            "$set": {
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "updatedAt": now,
                "lastLoginAt": now,
            },
            "$inc": {"loginCount": 1},
            "$setOnInsert": {"createdAt": now},
        },
        upsert=True,
    )
    doc = await db.users.find_one({"_id": user.id})
    return _to_user(doc) if doc else user


async def find_by_id(user_id: str) -> AuthUser | None:
    db = get_db()
    if db is None:
        return None
    doc = await db.users.find_one({"_id": user_id})
    if not doc:
        return None
    return _to_user(doc)
