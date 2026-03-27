from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.aggregator.report_builder import create_pending_report
from app.db.mongo import get_report, list_reports, save_report
from app.logging_config import trace_id_var
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, UXReport
from app.pipeline.orchestrator import run_pipeline

router = APIRouter(prefix="/api", tags=["reports"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def start_analysis(body: AnalyzeRequest, background_tasks: BackgroundTasks) -> AnalyzeResponse:
    if not body.url or not body.url.strip():
        raise HTTPException(status_code=400, detail="URL is required")

    report_id = str(uuid4())
    trace_id_var.set(report_id)

    selected = body.personaIds or []
    pending = create_pending_report(report_id, body.url, body.viewport, selected)
    await save_report(pending)

    background_tasks.add_task(
        run_pipeline,
        report_id,
        body.url,
        body.viewport,
        body.personaIds,
    )

    return AnalyzeResponse(
        reportId=report_id,
        message=f"Analysis started. Poll GET /api/reports/{report_id} for results.",
    )


@router.get("/reports/{report_id}", response_model=UXReport)
async def get_report_by_id(report_id: str) -> UXReport:
    report = await get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/reports", response_model=list[UXReport])
async def get_all_reports() -> list[UXReport]:
    return await list_reports()
