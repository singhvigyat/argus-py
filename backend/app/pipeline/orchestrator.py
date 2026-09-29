import asyncio
import time
from urllib.parse import urlparse

from app.aggregator.conflict_detector import detect_conflicts
from app.aggregator.issue_verifier import verify_issues
from app.aggregator.report_builder import assemble_report, attach_verification
from app.agents.persona_analyzer import load_som_screenshot, run_persona_agent
from app.agents.personas import ALL_PERSONAS
from app.auth.usage import finish_job
from app.config import get_settings
from app.crawler.screenshot import capture_screenshots, load_ui_structure
from app.db.jobs import get_job, patch_job, put_job
from app.logging_config import get_logger, trace_id_var
from app.models.schemas import Artifacts, PersonaAnalysis, Viewport

logger = get_logger(__name__)


def normalize_url(url: str) -> str:
    normalized = url if url.startswith(("http://", "https://")) else f"https://{url}"
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Invalid URL format. Please include http:// or https://")
    return normalized


async def run_pipeline(
    job_id: str,
    url: str,
    viewport: Viewport = "desktop",
    persona_ids: list[str] | None = None,
    user_id: str | None = None,
) -> None:
    trace_id_var.set(job_id)
    settings = get_settings()

    try:
        await asyncio.wait_for(
            _run_stages(job_id, url, viewport, persona_ids),
            timeout=settings.pipeline_timeout_seconds,
        )
    except TimeoutError:
        logger.error("Pipeline timed out after %ds", settings.pipeline_timeout_seconds)
        await patch_job(job_id, status="error", error="Pipeline timed out")
    except Exception as exc:
        message = str(exc).strip() or type(exc).__name__
        logger.exception("Pipeline failed: %s", message)
        await patch_job(job_id, status="error", error=message)
    finally:
        if user_id:
            await finish_job(user_id, job_id)


async def _run_stages(
    job_id: str,
    url: str,
    viewport: Viewport,
    persona_ids: list[str] | None,
) -> None:
    start = time.monotonic()
    normalized_url = normalize_url(url)
    active_personas = (
        [p for p in ALL_PERSONAS if p.id in persona_ids]
        if persona_ids
        else ALL_PERSONAS
    )
    selected = [p.id for p in active_personas]

    await patch_job(job_id, status="processing", url=normalized_url, selectedPersonas=selected)

    logger.info("Stage 1/6 — DOM extraction + Playwright screenshots")
    screenshots, job_dir = await capture_screenshots(normalized_url, job_id)
    await patch_job(job_id, screenshots=screenshots)

    logger.info("Stage 2/6 — Loading SoM-labeled screenshot for %s", viewport)
    ui_structure = load_ui_structure(job_dir, viewport)
    som_bytes = await load_som_screenshot(job_dir, viewport)
    artifacts = Artifacts(
        screenshots={
            "raw": f"/screenshots/{job_id}/{viewport}.png",
            "som": f"/screenshots/{job_id}/som-{viewport}.png",
        },
        domStructure=f"/screenshots/{job_id}/ui-structure-{viewport}.json",
    )
    await patch_job(job_id, artifacts=artifacts)

    logger.info("Stage 3/6 — Vision analysis: %d persona agents via asyncio.gather", len(active_personas))

    async def _run_agent(persona) -> PersonaAnalysis | None:
        return await run_persona_agent(persona, som_bytes, ui_structure, viewport)

    agent_results = await asyncio.gather(
        *[_run_agent(p) for p in active_personas],
        return_exceptions=True,
    )

    analyses: list[PersonaAnalysis] = []
    for persona, result in zip(active_personas, agent_results):
        if isinstance(result, Exception):
            logger.error("[%s] Agent failed: %s", persona.name, result)
            continue
        if result is None:
            logger.error("[%s] Agent returned null", persona.name)
            continue
        analyses.append(result)
        logger.info("[%s] complete — score %.1f/10, %d issues", persona.name, result.overallScore, len(result.issues))

    await patch_job(job_id, personaInsights=analyses)

    logger.info("Stage 4/6 — DOM-backed claim verification")
    verification_results = verify_issues(analyses, ui_structure)
    sanitized, verification_summary = attach_verification(analyses, verification_results)

    logger.info("Stage 5/6 — Conflict detection (deterministic + semantic)")
    conflict_report = await detect_conflicts(sanitized)

    logger.info("Stage 6/6 — Verified report assembly + persistence")
    elapsed_ms = int((time.monotonic() - start) * 1000)
    report = assemble_report(
        job_id=job_id,
        url=normalized_url,
        viewport=viewport,
        analyses=sanitized,
        screenshots=screenshots,
        artifacts=artifacts,
        analysis_time_ms=elapsed_ms,
        selected_personas=selected,
        verification_results=verification_results,
        verification_summary=verification_summary,
        conflict_report=conflict_report,
    )
    existing = await get_job(job_id)
    if existing:
        report = report.model_copy(update={"createdAt": existing.createdAt, "ownerId": existing.ownerId})
    await put_job(report)
    logger.info("Pipeline complete in %.1fs — %d conflicts found", elapsed_ms / 1000, conflict_report.totalConflicts)
