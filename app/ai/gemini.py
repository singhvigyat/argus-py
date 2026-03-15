import asyncio
import re
import time
from enum import Enum

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_last_call_timestamp: float = 0.0
_call_lock = asyncio.Lock()


class GeminiErrorKind(str, Enum):
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    SERVER = "server"
    OTHER = "other"


def _classify_error(exc: Exception) -> GeminiErrorKind:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    message = str(exc).lower()

    if status == 401 or "unauthorized" in message or "invalid api key" in message:
        return GeminiErrorKind.AUTH
    if status == 429 or "resource_exhausted" in message or "429" in message or "quota" in message:
        return GeminiErrorKind.RATE_LIMIT
    if status and int(status) >= 500:
        return GeminiErrorKind.SERVER
    if "internal" in message or "unavailable" in message or "503" in message:
        return GeminiErrorKind.SERVER
    return GeminiErrorKind.OTHER


def _is_retryable(exc: Exception) -> bool:
    kind = _classify_error(exc)
    return kind in (GeminiErrorKind.RATE_LIMIT, GeminiErrorKind.SERVER)


def _extract_retry_delay(exc: Exception) -> float:
    match = re.search(r"retry in ([\d.]+)s", str(exc), re.IGNORECASE)
    if match:
        return float(match.group(1)) + 2.0
    return 65.0


def _get_client() -> genai.Client:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env")
    return genai.Client(api_key=settings.gemini_api_key)


async def _enforce_call_spacing() -> None:
    global _last_call_timestamp
    settings = get_settings()
    min_delay = settings.min_gemini_call_delay_seconds
    async with _call_lock:
        elapsed = time.monotonic() - _last_call_timestamp
        if elapsed < min_delay:
            wait = min_delay - elapsed
            logger.info("Spacing Gemini calls — waiting %.1fs", wait)
            await asyncio.sleep(wait)
        _last_call_timestamp = time.monotonic()


def _sync_generate(client: genai.Client, model: str, contents: list) -> str:
    response = client.models.generate_content(model=model, contents=contents)
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=4, max=90),
    reraise=True,
)
async def _call_with_retry(model: str, contents: list) -> str:
    await _enforce_call_spacing()
    client = _get_client()

    try:
        return await asyncio.to_thread(_sync_generate, client, model, contents)
    except genai_errors.ClientError as exc:
        kind = _classify_error(exc)
        if kind == GeminiErrorKind.AUTH:
            logger.error("Gemini auth failure (401) — check GEMINI_API_KEY")
            raise RuntimeError("Gemini authentication failed. Check GEMINI_API_KEY.") from exc
        if kind == GeminiErrorKind.RATE_LIMIT:
            delay = _extract_retry_delay(exc)
            logger.warning("Gemini rate limit (429) — backing off %.1fs", delay)
            await asyncio.sleep(delay)
        raise


async def analyze_image_with_gemini(image_bytes: bytes, prompt: str) -> str:
    settings = get_settings()
    contents: list = [
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        prompt,
    ]
    try:
        return await _call_with_retry(settings.gemini_model, contents)
    except RetryError as exc:
        raise RuntimeError(f"Gemini vision call failed after retries: {exc.last_attempt.exception()}") from exc


async def analyze_text_with_gemini(prompt: str) -> str:
    settings = get_settings()
    try:
        return await _call_with_retry(settings.gemini_model, [prompt])
    except RetryError as exc:
        raise RuntimeError(f"Gemini text call failed after retries: {exc.last_attempt.exception()}") from exc
