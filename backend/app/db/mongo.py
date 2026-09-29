from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_mongo_ok = False


def mongo_available() -> bool:
    return _mongo_ok


def mongo_configured() -> bool:
    return bool(get_settings().mongodb_uri)


def get_db() -> AsyncIOMotorDatabase | None:
    if not _mongo_ok:
        return None
    return _db


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email")
    await db.login_events.create_index([("userId", 1), ("createdAt", -1)])
    await db.login_events.create_index("createdAt")
    await db.reports.create_index("jobId", unique=True)
    await db.reports.create_index([("userId", 1), ("createdAt", -1)])
    await db.reports.create_index("status")
    await db.usage_daily.create_index([("userId", 1), ("date", 1)], unique=True)
    await db.usage_global.create_index("date", unique=True)


async def connect_mongo() -> None:
    global _client, _db, _mongo_ok
    settings = get_settings()
    if not settings.mongodb_uri:
        logger.info("MONGODB_URI not set — users, quota, and reports stay in memory / usage.json")
        return
    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
        _db = _client[settings.mongodb_database]
        await _db.command("ping")
        await _ensure_indexes(_db)
        _mongo_ok = True
        logger.info("Connected to MongoDB at %s", settings.mongodb_uri)
    except Exception as exc:
        _mongo_ok = False
        logger.warning("MongoDB unavailable — using in-memory / file fallback: %s", exc)


async def disconnect_mongo() -> None:
    global _client, _db, _mongo_ok
    if _client:
        _client.close()
        _client = None
        _db = None
        _mongo_ok = False
        logger.info("Disconnected from MongoDB")


async def ping_mongo() -> bool:
    if not _mongo_ok or _db is None:
        return False
    try:
        await _db.command("ping")
        return True
    except Exception:
        return False
