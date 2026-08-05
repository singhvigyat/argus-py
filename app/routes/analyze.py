from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request

from app.aggregator.report_builder import create_pending_report
from app.auth.deps import require_user
from app.auth.usage import try_start_job
from app.db.jobs import get_job, get_owner, list_jobs, put_job
from app.errors import ApiError
from app.logging_config import trace_id_var
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, UXReport
from app.pipeline.orchestrator import normalize_url, run_pipeline

router = APIRouter(tags=["analyze"])


@router.post("/api/analyze", response_model=AnalyzeResponse, status_code=202)
async def start_analysis(
    body: AnalyzeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> AnalyzeResponse:
    user = require_user(request)

    if not body.url or not body.url.strip():
        raise ApiError(400, "URL is required")

    try:
        normalized = normalize_url(body.url.strip())
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc

    job_id = str(uuid4())
    ok, status, error, code, quota = try_start_job(user.id, job_id)
    if not ok:
        raise ApiError(status, error, code=code, quota=quota.model_dump())

    trace_id_var.set(job_id)
    selected = body.personaIds or []
    pending = create_pending_report(job_id, normalized, body.viewport, selected)
    await put_job(pending, owner_id=user.id)

    background_tasks.add_task(
        run_pipeline,
        job_id,
        normalized,
        body.viewport,
        body.personaIds,
        user.id,
    )

    return AnalyzeResponse(
        jobId=job_id,
        message="Analysis started. Poll GET /api/analyze/:jobId for results.",
        quota=quota,
    )


@router.get("/api/analyze/{job_id}", response_model=UXReport, response_model_exclude={"ownerId"})
async def get_analysis_status(job_id: str, request: Request) -> UXReport:
    user = require_user(request)
    job = await get_job(job_id)
    owner = get_owner(job_id)
    if not job or owner != user.id:
        raise ApiError(404, "Job not found")
    return job


@router.get("/api/reports", response_model=list[UXReport], response_model_exclude={"ownerId"})
async def get_all_reports(request: Request) -> list[UXReport]:
    user = require_user(request)
    jobs = await list_jobs()
    return [job for job in jobs if get_owner(job.jobId) == user.id]


@router.get("/api/reports/{report_id}", response_model=UXReport, response_model_exclude={"ownerId"})
async def get_report_by_id(report_id: str, request: Request) -> UXReport:
    return await get_analysis_status(report_id, request)
