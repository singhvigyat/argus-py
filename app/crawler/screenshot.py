import asyncio
import json
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

from app.config import get_settings
from app.crawler.dom_script import DOM_EXTRACTION_SCRIPT
from app.crawler.som import generate_labeled_screenshot
from app.logging_config import get_logger
from app.models.schemas import DOMElement, ScreenshotSet, UIStructure, Viewport

logger = get_logger(__name__)

VIEWPORTS: dict[Viewport, dict[str, int | str]] = {
    "desktop": {
        "width": 1280,
        "height": 720,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    },
    "tablet": {
        "width": 768,
        "height": 1024,
        "user_agent": (
            "Mozilla/5.0 (iPad; CPU OS 13_3 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/13.0.4 Mobile/15E148 Safari/604.1"
        ),
    },
    "mobile": {
        "width": 375,
        "height": 812,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
        ),
    },
}


def _navigate_safely(page: Page, url: str) -> None:
    try:
        page.goto(url, wait_until="networkidle", timeout=30_000)
    except Exception:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(2000)
        except Exception as exc:
            raise RuntimeError(f"Failed to load URL: {url}. {exc}") from exc


def _extract_dom(page: Page) -> list[DOMElement]:
    raw = page.evaluate(DOM_EXTRACTION_SCRIPT)
    return [DOMElement.model_validate(item) for item in raw]


def _build_ui_structure(viewport: Viewport, width: int, elements: list[DOMElement]) -> UIStructure:
    sections: dict[str, list[int]] = {}
    for el in elements:
        sections.setdefault(el.section or "content", []).append(el.id)
    return UIStructure(
        viewport=viewport,
        pageWidth=width,
        elementCount=len(elements),
        sections=sections,
        elements=elements,
    )


def _write_json(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _capture_viewport(
    browser: Browser,
    url: str,
    viewport: Viewport,
    job_dir: Path,
) -> None:
    cfg = VIEWPORTS[viewport]
    context = browser.new_context(
        viewport={"width": int(cfg["width"]), "height": int(cfg["height"])},
        user_agent=str(cfg["user_agent"]),
    )
    page = context.new_page()
    try:
        _navigate_safely(page, url)
        elements = _extract_dom(page)
        logger.info("Extracted %d DOM elements for %s", len(elements), viewport)

        screenshot_path = job_dir / f"{viewport}.png"
        page.screenshot(path=str(screenshot_path), type="png")

        dom_data = {"viewport": viewport, "width": cfg["width"], "elements": [e.model_dump() for e in elements]}
        _write_json(job_dir / f"dom-{viewport}.json", dom_data)

        ui_structure = _build_ui_structure(viewport, int(cfg["width"]), elements)
        _write_json(job_dir / f"ui-structure-{viewport}.json", ui_structure.model_dump())

        generate_labeled_screenshot(
            screenshot_path,
            elements,
            job_dir / f"som-{viewport}.png",
        )
    finally:
        context.close()


def _capture_screenshots_sync(url: str, job_id: str) -> tuple[ScreenshotSet, str]:
    settings = get_settings()
    job_dir = Path(settings.screenshots_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            for viewport in ("desktop", "tablet", "mobile"):
                _capture_viewport(browser, url, viewport, job_dir)
        finally:
            browser.close()

    return (
        ScreenshotSet(
            desktop=f"/screenshots/{job_id}/desktop.png",
            tablet=f"/screenshots/{job_id}/tablet.png",
            mobile=f"/screenshots/{job_id}/mobile.png",
        ),
        str(job_dir),
    )


async def capture_screenshots(url: str, job_id: str) -> tuple[ScreenshotSet, Path]:
    # Sync Playwright in a thread — uvicorn on Windows uses SelectorEventLoop,
    # which cannot spawn subprocesses (Playwright async API raises NotImplementedError).
    screenshots, job_dir = await asyncio.to_thread(_capture_screenshots_sync, url, job_id)
    return screenshots, Path(job_dir)


def load_ui_structure(job_dir: Path, viewport: Viewport) -> UIStructure:
    path = job_dir / f"ui-structure-{viewport}.json"
    if not path.exists():
        return UIStructure(viewport=viewport)
    return UIStructure.model_validate_json(path.read_text(encoding="utf-8"))
