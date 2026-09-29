import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock

from app.config import BACKEND_ROOT, get_settings
from app.db.mongo import mongo_available
from app.db.usage import finish_job as mongo_finish_job
from app.db.usage import get_quota as mongo_get_quota
from app.db.usage import try_start_job as mongo_try_start_job
from app.logging_config import get_logger
from app.models.schemas import QuotaSnapshot

logger = get_logger(__name__)

DATA_FILE = BACKEND_ROOT / "data" / "usage.json"
_lock = Lock()


@dataclass
class UsageRecord:
    count: int = 0
    date: str = ""
    active_job_id: str | None = None


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def next_reset_at() -> str:
    now = datetime.now(timezone.utc)
    reset = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
    return reset.isoformat().replace("+00:00", "Z")


def _empty() -> UsageRecord:
    return UsageRecord(count=0, date=_today_utc(), active_job_id=None)


def _fresh(raw: dict | None) -> UsageRecord:
    if not raw:
        return _empty()
    record = UsageRecord(
        count=int(raw.get("count") or 0),
        date=str(raw.get("date") or ""),
        active_job_id=raw.get("activeJobId") or raw.get("active_job_id"),
    )
    if record.date != _today_utc():
        return _empty()
    return record


def _load() -> dict:
    try:
        parsed = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return {
            "users": parsed.get("users") or {},
            "global": parsed.get("global") or {},
        }
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"users": {}, "global": {}}


def _save(cache: dict) -> None:
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not persist usage file: %s", exc)


def _quota(record: UsageRecord, limit: int) -> QuotaSnapshot:
    return QuotaSnapshot(
        used=record.count,
        limit=limit,
        remaining=max(0, limit - record.count),
        resetAt=next_reset_at(),
    )


def get_limits() -> tuple[int, int]:
    settings = get_settings()
    return settings.daily_analysis_limit, settings.global_daily_limit


def _file_get_quota(user_id: str) -> QuotaSnapshot:
    daily, _ = get_limits()
    with _lock:
        cache = _load()
        return _quota(_fresh(cache["users"].get(user_id)), daily)


def _file_try_start_job(user_id: str, job_id: str) -> tuple[bool, int, str, str | None, QuotaSnapshot]:
    daily, server = get_limits()
    with _lock:
        cache = _load()
        user = _fresh(cache["users"].get(user_id))
        global_rec = _fresh(cache.get("global"))
        quota = _quota(user, daily)

        if user.active_job_id:
            return False, 409, "You already have a reading in progress. Wait for it to finish.", "JOB_IN_PROGRESS", quota
        if user.count >= daily:
            return (
                False,
                429,
                f"Daily limit reached ({daily} readings). Try again after midnight UTC.",
                "QUOTA_EXCEEDED",
                quota,
            )
        if global_rec.count >= server:
            return (
                False,
                429,
                "The shared daily capacity is full. Please try again tomorrow.",
                "GLOBAL_QUOTA_EXCEEDED",
                quota,
            )

        user.count += 1
        user.active_job_id = job_id
        global_rec.count += 1
        cache["users"][user_id] = {
            "count": user.count,
            "date": user.date,
            "activeJobId": user.active_job_id,
        }
        cache["global"] = {
            "count": global_rec.count,
            "date": global_rec.date,
            "activeJobId": None,
        }
        _save(cache)
        return True, 200, "", None, _quota(user, daily)


def _file_finish_job(user_id: str, job_id: str) -> None:
    with _lock:
        cache = _load()
        user = _fresh(cache["users"].get(user_id))
        if user.active_job_id == job_id:
            user.active_job_id = None
            cache["users"][user_id] = {
                "count": user.count,
                "date": user.date,
                "activeJobId": None,
            }
            _save(cache)


async def get_quota(user_id: str) -> QuotaSnapshot:
    if mongo_available():
        return await mongo_get_quota(user_id, next_reset_at())
    return _file_get_quota(user_id)


async def try_start_job(user_id: str, job_id: str) -> tuple[bool, int, str, str | None, QuotaSnapshot]:
    if mongo_available():
        return await mongo_try_start_job(user_id, job_id, next_reset_at())
    return _file_try_start_job(user_id, job_id)


async def finish_job(user_id: str, job_id: str) -> None:
    if mongo_available():
        await mongo_finish_job(user_id, job_id)
        return
    _file_finish_job(user_id, job_id)
