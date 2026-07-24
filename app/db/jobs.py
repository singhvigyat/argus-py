from app.db.mongo import get_report as mongo_get
from app.db.mongo import list_reports as mongo_list
from app.db.mongo import save_report as mongo_save
from app.logging_config import get_logger
from app.models.schemas import UXReport

logger = get_logger(__name__)

_jobs: dict[str, UXReport] = {}
_owners: dict[str, str] = {}


def get_owner(job_id: str) -> str | None:
    if job_id in _owners:
        return _owners[job_id]
    job = _jobs.get(job_id)
    return job.ownerId if job else None


async def put_job(report: UXReport, owner_id: str | None = None) -> UXReport:
    if owner_id:
        report = report.model_copy(update={"ownerId": owner_id})
        _owners[report.jobId] = owner_id
    elif report.ownerId:
        _owners[report.jobId] = report.ownerId
    _jobs[report.jobId] = report
    try:
        await mongo_save(report)
    except Exception as exc:
        logger.debug("Mongo persist skipped for %s: %s", report.jobId, exc)
    return report


async def patch_job(job_id: str, **updates) -> UXReport | None:
    current = _jobs.get(job_id)
    if current is None:
        return None
    updated = current.model_copy(update=updates)
    _jobs[job_id] = updated
    try:
        await mongo_save(updated)
    except Exception as exc:
        logger.debug("Mongo persist skipped for %s: %s", job_id, exc)
    return updated


async def get_job(job_id: str) -> UXReport | None:
    job = _jobs.get(job_id)
    if job:
        return job
    job = await mongo_get(job_id)
    if job and job.ownerId:
        _jobs[job_id] = job
        _owners[job_id] = job.ownerId
    return job


async def list_jobs(limit: int = 50) -> list[UXReport]:
    memory = sorted(_jobs.values(), key=lambda r: r.createdAt, reverse=True)[:limit]
    if memory:
        return memory
    return await mongo_list(limit)
