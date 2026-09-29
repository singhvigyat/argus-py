from datetime import timedelta

from app.config import get_settings
from app.db.mongo import get_db
from app.db.util import as_utc, parse_dt, utc_now
from app.logging_config import get_logger
from app.models.schemas import ReportListItem, ScreenshotSet, UXReport

logger = get_logger(__name__)

_OVERLAY_KEYS = {
    "jobId",
    "ownerId",
    "url",
    "status",
    "severityScore",
    "createdAt",
    "completedAt",
    "screenshots",
    "error",
}


def _report_to_doc(report: UXReport) -> dict:
    data = report.model_dump(mode="python")
    owner = report.ownerId
    payload = {k: v for k, v in data.items() if k not in _OVERLAY_KEYS}
    return {
        "jobId": report.jobId,
        "userId": owner,
        "ownerId": owner,
        "url": report.url,
        "status": report.status,
        "severityScore": report.severityScore,
        "createdAt": as_utc(report.createdAt),
        "completedAt": as_utc(report.completedAt),
        "screenshots": data.get("screenshots") or {},
        "error": report.error,
        "payload": payload,
    }


def _doc_to_report(doc: dict) -> UXReport:
    payload = doc.get("payload")
    if isinstance(payload, dict):
        merged = dict(payload)
    else:
        merged = {k: v for k, v in doc.items() if k not in ("_id", "payload", "userId")}
    owner = doc.get("userId") or doc.get("ownerId") or merged.get("ownerId")
    merged["jobId"] = doc.get("jobId") or merged.get("jobId")
    merged["ownerId"] = owner
    if doc.get("url") is not None:
        merged["url"] = doc["url"]
    if doc.get("status") is not None:
        merged["status"] = doc["status"]
    if doc.get("severityScore") is not None:
        merged["severityScore"] = doc["severityScore"]
    if doc.get("createdAt") is not None:
        merged["createdAt"] = doc["createdAt"]
    if "completedAt" in doc:
        merged["completedAt"] = doc.get("completedAt")
    if doc.get("screenshots") is not None:
        merged["screenshots"] = doc["screenshots"]
    if "error" in doc:
        merged["error"] = doc.get("error")
    merged.pop("userId", None)
    merged.pop("payload", None)
    merged.pop("_id", None)
    return UXReport.model_validate(merged)


def _desktop_shot(doc: dict) -> str:
    shots = doc.get("screenshots") or {}
    if isinstance(shots, ScreenshotSet):
        return shots.desktop or ""
    if isinstance(shots, dict):
        return str(shots.get("desktop") or "")
    return ""


def _doc_to_list_item(doc: dict) -> ReportListItem:
    created = parse_dt(doc.get("createdAt")) or utc_now()
    return ReportListItem(
        jobId=str(doc.get("jobId") or ""),
        url=str(doc.get("url") or ""),
        status=doc.get("status") or "pending",
        severityScore=float(doc.get("severityScore") or 0),
        createdAt=created,
        completedAt=parse_dt(doc.get("completedAt")),
        screenshot=_desktop_shot(doc),
    )


async def save_report(report: UXReport) -> None:
    db = get_db()
    if db is None:
        return
    doc = _report_to_doc(report)
    await db.reports.update_one({"jobId": report.jobId}, {"$set": doc}, upsert=True)


async def get_report(job_id: str) -> UXReport | None:
    db = get_db()
    if db is None:
        return None
    doc = await db.reports.find_one({"jobId": job_id})
    if not doc:
        return None
    return _doc_to_report(doc)


async def get_owned_report(job_id: str, user_id: str) -> UXReport | None:
    db = get_db()
    if db is None:
        return None
    doc = await db.reports.find_one(
        {
            "jobId": job_id,
            "$or": [{"userId": user_id}, {"ownerId": user_id}],
        }
    )
    if not doc:
        return None
    return _doc_to_report(doc)


async def list_report_items(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> list[ReportListItem]:
    db = get_db()
    if db is None:
        return []
    query: dict = {"$or": [{"userId": user_id}, {"ownerId": user_id}]}
    if status:
        query["status"] = status
    cursor = (
        db.reports.find(
            query,
            {
                "_id": 0,
                "jobId": 1,
                "url": 1,
                "status": 1,
                "severityScore": 1,
                "createdAt": 1,
                "completedAt": 1,
                "screenshots": 1,
            },
        )
        .sort("createdAt", -1)
        .skip(offset)
        .limit(limit)
    )
    return [_doc_to_list_item(doc) async for doc in cursor]


async def sweep_stale_jobs() -> int:
    db = get_db()
    if db is None:
        return 0
    minutes = get_settings().stale_job_minutes
    cutoff = utc_now() - timedelta(minutes=minutes)
    stale_ids: list[str] = []
    pairs: list[tuple[str, str]] = []
    async for doc in db.reports.find({"status": {"$in": ["pending", "processing"]}}):
        created = parse_dt(doc.get("createdAt"))
        if created is None or created >= cutoff:
            continue
        job_id = str(doc.get("jobId") or "")
        if not job_id:
            continue
        stale_ids.append(job_id)
        owner = doc.get("userId") or doc.get("ownerId")
        if owner:
            pairs.append((str(owner), job_id))

    if not stale_ids:
        return 0

    message = f"Job timed out (stale after {minutes} minutes)"
    await db.reports.update_many(
        {"jobId": {"$in": stale_ids}},
        {"$set": {"status": "error", "error": message}},
    )
    for user_id, job_id in pairs:
        await db.usage_daily.update_many(
            {"userId": user_id, "activeJobId": job_id},
            {"$set": {"activeJobId": None}},
        )
    logger.warning("Swept %d stale job(s): %s", len(stale_ids), ", ".join(stale_ids))
    return len(stale_ids)
