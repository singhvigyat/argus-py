from pymongo import ReturnDocument

from app.config import get_settings
from app.db.mongo import get_db
from app.db.util import today_utc
from app.logging_config import get_logger
from app.models.schemas import QuotaSnapshot

logger = get_logger(__name__)


def _quota(count: int, limit: int, reset_at: str) -> QuotaSnapshot:
    return QuotaSnapshot(
        used=count,
        limit=limit,
        remaining=max(0, limit - count),
        resetAt=reset_at,
    )


async def get_quota(user_id: str, reset_at: str) -> QuotaSnapshot:
    daily = get_settings().daily_analysis_limit
    db = get_db()
    if db is None:
        return _quota(0, daily, reset_at)
    rec = await db.usage_daily.find_one({"userId": user_id, "date": today_utc()})
    count = int(rec.get("count") or 0) if rec else 0
    return _quota(count, daily, reset_at)


async def try_start_job(
    user_id: str,
    job_id: str,
    reset_at: str,
) -> tuple[bool, int, str, str | None, QuotaSnapshot]:
    settings = get_settings()
    daily = settings.daily_analysis_limit
    server = settings.global_daily_limit
    date = today_utc()
    db = get_db()
    if db is None:
        raise RuntimeError("MongoDB is not available")

    await db.usage_daily.update_one(
        {"userId": user_id, "date": date},
        {"$setOnInsert": {"userId": user_id, "date": date, "count": 0, "activeJobId": None}},
        upsert=True,
    )
    await db.usage_global.update_one(
        {"date": date},
        {"$setOnInsert": {"date": date, "count": 0}},
        upsert=True,
    )

    user_rec = await db.usage_daily.find_one({"userId": user_id, "date": date})
    quota = _quota(int((user_rec or {}).get("count") or 0), daily, reset_at)

    if user_rec and user_rec.get("activeJobId"):
        return False, 409, "You already have a reading in progress. Wait for it to finish.", "JOB_IN_PROGRESS", quota
    if user_rec and int(user_rec.get("count") or 0) >= daily:
        return (
            False,
            429,
            f"Daily limit reached ({daily} readings). Try again after midnight UTC.",
            "QUOTA_EXCEEDED",
            quota,
        )

    global_rec = await db.usage_global.find_one({"date": date})
    if global_rec and int(global_rec.get("count") or 0) >= server:
        return (
            False,
            429,
            "The shared daily capacity is full. Please try again tomorrow.",
            "GLOBAL_QUOTA_EXCEEDED",
            quota,
        )

    updated_user = await db.usage_daily.find_one_and_update(
        {
            "userId": user_id,
            "date": date,
            "count": {"$lt": daily},
            "$or": [{"activeJobId": None}, {"activeJobId": {"$exists": False}}],
        },
        {"$inc": {"count": 1}, "$set": {"activeJobId": job_id}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated_user:
        latest = await db.usage_daily.find_one({"userId": user_id, "date": date})
        latest_quota = _quota(int((latest or {}).get("count") or 0), daily, reset_at)
        if latest and latest.get("activeJobId"):
            return False, 409, "You already have a reading in progress. Wait for it to finish.", "JOB_IN_PROGRESS", latest_quota
        return (
            False,
            429,
            f"Daily limit reached ({daily} readings). Try again after midnight UTC.",
            "QUOTA_EXCEEDED",
            latest_quota,
        )

    updated_global = await db.usage_global.find_one_and_update(
        {"date": date, "count": {"$lt": server}},
        {"$inc": {"count": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated_global:
        await db.usage_daily.update_one(
            {"userId": user_id, "date": date, "activeJobId": job_id},
            {"$inc": {"count": -1}, "$set": {"activeJobId": None}},
        )
        rolled = await db.usage_daily.find_one({"userId": user_id, "date": date})
        rolled_quota = _quota(max(0, int((rolled or {}).get("count") or 0)), daily, reset_at)
        return (
            False,
            429,
            "The shared daily capacity is full. Please try again tomorrow.",
            "GLOBAL_QUOTA_EXCEEDED",
            rolled_quota,
        )

    return True, 200, "", None, _quota(int(updated_user.get("count") or 0), daily, reset_at)


async def finish_job(user_id: str, job_id: str) -> None:
    db = get_db()
    if db is None:
        return
    result = await db.usage_daily.update_many(
        {"userId": user_id, "activeJobId": job_id},
        {"$set": {"activeJobId": None}},
    )
    if result.modified_count:
        logger.debug("Cleared in-flight job %s for user %s", job_id, user_id)
