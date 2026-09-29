from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-2.0-flash"
    min_gemini_call_delay_seconds: float = 20.0
    gemini_timeout_seconds: float = 120.0

    mongodb_uri: str = ""
    mongodb_database: str = "argus"
    stale_job_minutes: int = 20

    port: int = 8000
    pipeline_timeout_seconds: int = 600
    screenshots_dir: str = "screenshots"

    google_client_id: str = ""
    session_secret: str = ""
    frontend_url: str = "http://localhost:5173"
    node_env: str = "development"

    daily_analysis_limit: int = 3
    global_daily_limit: int = 40

    @property
    def screenshots_path(self) -> Path:
        path = Path(self.screenshots_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path

    @property
    def is_production(self) -> bool:
        return self.node_env.lower() == "production"

    @property
    def auth_configured(self) -> bool:
        return bool(self.google_client_id and self.session_secret)

    @property
    def cors_origins(self) -> list[str]:
        origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
        if self.frontend_url:
            origins.append(self.frontend_url.rstrip("/"))
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()
