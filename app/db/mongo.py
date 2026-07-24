from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings
from app.logging_config import get_logger
from app.models.schemas import UXReport

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_mongo_ok = False


def mongo_available() -> bool:
    return _mongo_ok


async def connect_mongo() -> None:
    global _client, _db, _mongo_ok
    settings = get_settings()
    if not settings.mongodb_uri:
        logger.info("MONGODB_URI not set — using in-memory job store")
        return
    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
        _db = _client[settings.mongodb_database]
        await _db.command("ping")
        await _db.reports.create_index("jobId", unique=True)
        await _db.reports.create_index("createdAt")
        _mongo_ok = True
        logger.info("Connected to MongoDB at %s", settings.mongodb_uri)
    except Exception as exc:
        _mongo_ok = False
        logger.warning("MongoDB unavailable — using in-memory job store: %s", exc)


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


async def save_report(report: UXReport) -> None:
    if not _mongo_ok or _db is None:
        return
    data = report.model_dump(mode="json")
    await _db.reports.update_one({"jobId": report.jobId}, {"$set": data}, upsert=True)


async def get_report(report_id: str) -> UXReport | None:
    if not _mongo_ok or _db is None:
        return None
    doc = await _db.reports.find_one({"jobId": report_id}, {"_id": 0})
    if not doc:
        return None
    return UXReport.model_validate(doc)


async def list_reports(limit: int = 50) -> list[UXReport]:
    if not _mongo_ok or _db is None:
        return []
    cursor = _db.reports.find({}, {"_id": 0}).sort("createdAt", -1).limit(limit)
    return [UXReport.model_validate(doc) async for doc in cursor]


async def update_report_fields(report_id: str, **updates: Any) -> None:
    if not _mongo_ok or _db is None:
        return
    await _db.reports.update_one({"jobId": report_id}, {"$set": updates})
