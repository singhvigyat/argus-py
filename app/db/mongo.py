from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings
from app.logging_config import get_logger
from app.models.schemas import UXReport

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_mongo() -> None:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_database]
    await _db.reports.create_index("id", unique=True)
    await _db.reports.create_index("createdAt")
    logger.info("Connected to MongoDB at %s", settings.mongodb_uri)


async def disconnect_mongo() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("Disconnected from MongoDB")


def _get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB not connected")
    return _db


def _serialize_report(report: UXReport) -> dict[str, Any]:
    data = report.model_dump(mode="json")
    return data


async def save_report(report: UXReport) -> None:
    db = _get_db()
    data = _serialize_report(report)
    await db.reports.update_one({"id": report.id}, {"$set": data}, upsert=True)


async def get_report(report_id: str) -> UXReport | None:
    db = _get_db()
    doc = await db.reports.find_one({"id": report_id}, {"_id": 0})
    if not doc:
        return None
    return UXReport.model_validate(doc)


async def list_reports(limit: int = 50) -> list[UXReport]:
    db = _get_db()
    cursor = db.reports.find({}, {"_id": 0}).sort("createdAt", -1).limit(limit)
    return [UXReport.model_validate(doc) async for doc in cursor]


async def update_report_status(report_id: str, **updates: Any) -> None:
    db = _get_db()
    updates["updatedAt"] = datetime.utcnow()
    await db.reports.update_one({"id": report_id}, {"$set": updates})
