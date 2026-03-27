from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db.mongo import connect_mongo, disconnect_mongo
from app.logging_config import setup_logging
from app.routes.reports import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    settings = get_settings()
    Path(settings.screenshots_dir).mkdir(parents=True, exist_ok=True)
    await connect_mongo()
    yield
    await disconnect_mongo()


app = FastAPI(
    title="Argus",
    description="AI-native UX testing pipeline — multi-agent web interface evaluation",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
screenshots_path = Path(settings.screenshots_dir)
screenshots_path.mkdir(parents=True, exist_ok=True)

app.include_router(router)
app.mount("/screenshots", StaticFiles(directory=str(screenshots_path)), name="screenshots")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "argus"}
