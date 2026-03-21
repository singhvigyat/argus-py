import asyncio
import time
from urllib.parse import urlparse
from uuid import uuid4

from app.aggregator.report_builder import assemble_report, create_pending_report
from app.agents.persona_analyzer import load_som_screenshot, run_persona_agent
from app.agents.personas import ALL_PERSONAS
from app.config import get_settings
from app.crawler.screenshot import capture_screenshots, load_ui_structure
from app.db.mongo import save_report, update_report_status
from app.logging_config import get_logger, trace_id_var
from app.models.schemas import Artifacts, PersonaAnalysis, Viewport

logger = get_logger(__name__)


def _normalize_url(url: str) -> str:
    normalized = url if url.startswith(("http://", "https://")) else f"https://{url}"
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid URL format. Use http:// or https://")
    return normalized


async def run_pipeline(
    report_id: str,
    url: str,
    viewport: Viewport = "desktop",
    persona_ids: list[str] | None = None,
) -> None:
    trace_id_var.set(report_id)
    settings = get_settings()
    start = time.monotonic()

    try:
        normalized_url = _normalize_url(url)
        active_personas = (
            [p for p in ALL_PERSONAS if p.id in persona_ids]
            if persona_ids
            else ALL_PERSONAS
        )
        selected = [p.id for p in active_personas]

        pending = create_pending_report(report_id, normalized_url, viewport, selected)
        await save_report(pending)
        await update_report_status(report_id, status="processing")

        # Stage 1: Playwright capture — DOM extraction + SoM labeling
        logger.info("Stage 1/6 — Capturing screenshots and extracting DOM")
        screenshots, job_dir = await capture_screenshots(normalized_url, report_id)

        # Stage 2: Load artifacts for analysis viewport
        logger.info("Stage 2/6 — Loading UI structure for %s", viewport)
        ui_structure = load_ui_structure(job_dir, viewport)
        som_bytes = await load_som_screenshot(job_dir, viewport)

        artifacts = Artifacts(
            screenshots={
                "raw": f"/screenshots/{report_id}/{viewport}.png",
                "som": f"/screenshots/{report_id}/som-{viewport}.png",
            },
            domStructure=f"/screenshots/{report_id}/ui-structure-{viewport}.json",
        )
        await update_report_status(report_id, screenshots=screenshots.model_dump(), artifacts=artifacts.model_dump())

        # Stage 3: Parallel persona agents (vision analysis)
        logger.info("Stage 3/6 — Running %d persona agents in parallel", len(active_personas))

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

        # Stage 4: DOM-backed verification (sync, no AI)
        logger.info("Stage 4/6 — Verifying DOM-backed claims")

        # Stage 5: Conflict detection (deterministic + semantic AI)
        logger.info("Stage 5/6 — Detecting cross-persona conflicts")

        # Stage 6: Report assembly + persistence
        logger.info("Stage 6/6 — Assembling and persisting report")
        elapsed_ms = int((time.monotonic() - start) * 1000)
        report = await asyncio.wait_for(
            assemble_report(
                report_id=report_id,
                url=normalized_url,
                viewport=viewport,
                analyses=analyses,
                ui_structure=ui_structure,
                screenshots=screenshots,
                artifacts=artifacts,
                analysis_time_ms=elapsed_ms,
                selected_personas=selected,
            ),
            timeout=settings.pipeline_timeout_seconds,
        )
        await save_report(report)
        logger.info("Pipeline complete in %.1fs — %d conflicts found", elapsed_ms / 1000, report.summary.totalConflicts)

    except asyncio.TimeoutError:
        logger.error("Pipeline timed out after %ds", settings.pipeline_timeout_seconds)
        await update_report_status(report_id, status="failed", error="Pipeline timed out")
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        await update_report_status(report_id, status="failed", error=str(exc))


def start_pipeline(
    url: str,
    viewport: Viewport = "desktop",
    persona_ids: list[str] | None = None,
) -> str:
    report_id = str(uuid4())
    asyncio.create_task(run_pipeline(report_id, url, viewport, persona_ids))
    return report_id
