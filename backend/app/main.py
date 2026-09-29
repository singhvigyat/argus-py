from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth.google import is_auth_configured
from app.config import get_settings
from app.db.mongo import connect_mongo, disconnect_mongo, mongo_configured, ping_mongo
from app.db.reports import sweep_stale_jobs
from app.errors import ApiError, api_error_handler
from app.logging_config import get_logger, setup_logging
from app.routes.analyze import router as analyze_router
from app.routes.auth import router as auth_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.screenshots_path.mkdir(parents=True, exist_ok=True)
    await connect_mongo()
    swept = await sweep_stale_jobs()
    if swept:
        logger.info("Marked %d stale in-flight job(s) as error", swept)
    logger.info("Gemini API key: %s", "loaded" if settings.gemini_api_key else "MISSING")
    logger.info("Google auth: %s", "configured" if is_auth_configured() else "MISSING GOOGLE_CLIENT_ID / SESSION_SECRET")
    yield
    await disconnect_mongo()


app = FastAPI(
    title="Argus",
    description="AI-native UX testing pipeline — multi-agent web interface evaluation",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
screenshots_path = settings.screenshots_path
screenshots_path.mkdir(parents=True, exist_ok=True)

app.add_exception_handler(ApiError, api_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

app.include_router(auth_router)
app.include_router(analyze_router)
app.mount("/screenshots", StaticFiles(directory=str(screenshots_path)), name="screenshots")


@app.get("/health")
async def health():
    db_up = await ping_mongo()
    configured = mongo_configured()
    body = {
        "status": "ok" if (db_up or not configured) else "degraded",
        "service": "argus",
        "db": "up" if db_up else ("unconfigured" if not configured else "down"),
    }
    if configured and not db_up:
        return JSONResponse(status_code=503, content=body)
    return body
