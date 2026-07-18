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

from app.ai.provider import VisionProvider
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


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    response = getattr(exc, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
    return None


def classify_error(exc: Exception) -> GeminiErrorKind:
    status = _status_code(exc)
    message = str(exc).lower()

    if status == 401 or "unauthorized" in message or "invalid api key" in message or "unauthenticated" in message:
        return GeminiErrorKind.AUTH
    if status == 429 or "resource_exhausted" in message or "429" in message or "quota" in message:
        return GeminiErrorKind.RATE_LIMIT
    if (
        isinstance(exc, TimeoutError)
        or isinstance(exc, genai_errors.ServerError)
        or (status is not None and status >= 500)
        or "timed out" in message
    ):
        return GeminiErrorKind.SERVER
    if "internal" in message or "unavailable" in message or "503" in message or "500" in message:
        return GeminiErrorKind.SERVER
    return GeminiErrorKind.OTHER


def _is_retryable(exc: Exception) -> bool:
    return classify_error(exc) in (GeminiErrorKind.RATE_LIMIT, GeminiErrorKind.SERVER)


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
    settings = get_settings()

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_generate, client, model, contents),
            timeout=settings.gemini_timeout_seconds,
        )
    except TimeoutError:
        logger.warning("Gemini call timed out after %.0fs (model=%s)", settings.gemini_timeout_seconds, model)
        raise
    except Exception as exc:
        kind = classify_error(exc)
        if kind == GeminiErrorKind.AUTH:
            logger.error("Gemini auth failure (401) — check GEMINI_API_KEY")
            raise RuntimeError("Gemini authentication failed. Check GEMINI_API_KEY.") from exc
        if kind == GeminiErrorKind.RATE_LIMIT:
            delay = _extract_retry_delay(exc)
            logger.warning("Gemini rate limit (429) — backing off %.1fs before retry", delay)
            await asyncio.sleep(delay)
            raise
        if kind == GeminiErrorKind.SERVER:
            logger.warning("Gemini server error (5xx) on %s: %s", model, exc)
            raise
        logger.error("Gemini non-retryable error: %s", exc)
        raise


async def _call_with_fallback(contents: list) -> str:
    settings = get_settings()
    primary = settings.gemini_model
    fallback = settings.gemini_fallback_model

    try:
        return await _call_with_retry(primary, contents)
    except RetryError as exc:
        inner = exc.last_attempt.exception() or exc
        kind = classify_error(inner) if inner else GeminiErrorKind.OTHER
        if kind == GeminiErrorKind.SERVER and fallback and fallback != primary:
            logger.warning("Primary model %s exhausted 5xx retries — falling back to %s", primary, fallback)
            try:
                return await _call_with_retry(fallback, contents)
            except RetryError as fallback_exc:
                raise RuntimeError(
                    f"Gemini call failed after retries on {primary} and {fallback}: "
                    f"{fallback_exc.last_attempt.exception()}"
                ) from fallback_exc
        raise RuntimeError(f"Gemini call failed after retries: {inner}") from exc
    except RuntimeError:
        raise
    except Exception as exc:
        kind = classify_error(exc)
        if kind == GeminiErrorKind.SERVER and fallback and fallback != primary:
            logger.warning("Primary model %s hit 5xx — falling back to %s", primary, fallback)
            return await _call_with_retry(fallback, contents)
        raise


class GeminiProvider:
    """Gemini vision/text backend with classified retries and model fallback."""

    async def analyze_image(self, image_bytes: bytes, prompt: str) -> str:
        contents: list = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            prompt,
        ]
        return await _call_with_fallback(contents)

    async def analyze_text(self, prompt: str) -> str:
        return await _call_with_fallback([prompt])


_provider: VisionProvider | None = None


def get_vision_provider() -> VisionProvider:
    global _provider
    if _provider is None:
        _provider = GeminiProvider()
    return _provider


async def analyze_image_with_gemini(image_bytes: bytes, prompt: str) -> str:
    return await get_vision_provider().analyze_image(image_bytes, prompt)


async def analyze_text_with_gemini(prompt: str) -> str:
    return await get_vision_provider().analyze_text(prompt)
