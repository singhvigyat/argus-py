from app.db.mongo import mongo_available
from app.db.reports import get_owned_report, get_report, list_report_items, save_report
from app.logging_config import get_logger
from app.models.schemas import ReportListItem, UXReport

logger = get_logger(__name__)

_jobs: dict[str, UXReport] = {}


def _to_list_item(report: UXReport) -> ReportListItem:
    return ReportListItem(
        jobId=report.jobId,
        url=report.url,
        status=report.status,
        severityScore=report.severityScore,
        createdAt=report.createdAt,
        completedAt=report.completedAt,
        screenshot=report.screenshots.desktop if report.screenshots else "",
    )


async def put_job(report: UXReport, owner_id: str | None = None) -> UXReport:
    if owner_id:
        report = report.model_copy(update={"ownerId": owner_id})
    _jobs[report.jobId] = report
    try:
        await save_report(report)
    except Exception as exc:
        logger.warning("Mongo persist skipped for %s: %s", report.jobId, exc)
    return report


async def patch_job(job_id: str, **updates) -> UXReport | None:
    current = await get_job(job_id)
    if current is None:
        return None
    updated = current.model_copy(update=updates)
    return await put_job(updated)


async def get_job(job_id: str) -> UXReport | None:
    job = _jobs.get(job_id)
    if job:
        return job
    job = await get_report(job_id)
    if job:
        _jobs[job_id] = job
    return job


async def get_owned_job(job_id: str, user_id: str) -> UXReport | None:
    job = _jobs.get(job_id)
    if job:
        return job if job.ownerId == user_id else None
    if mongo_available():
        job = await get_owned_report(job_id, user_id)
        if job:
            _jobs[job_id] = job
        return job
    return None


async def list_jobs_for_user(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> list[ReportListItem]:
    if mongo_available():
        return await list_report_items(user_id, limit=limit, offset=offset, status=status)
    jobs = [j for j in _jobs.values() if j.ownerId == user_id]
    if status:
        jobs = [j for j in jobs if j.status == status]
    jobs = sorted(jobs, key=lambda r: r.createdAt, reverse=True)
    return [_to_list_item(j) for j in jobs[offset : offset + limit]]
