from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    min_gemini_call_delay_seconds: float = 20.0
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "argus"
    port: int = 8000
    pipeline_timeout_seconds: int = 600
    screenshots_dir: str = "screenshots"


@lru_cache
def get_settings() -> Settings:
    return Settings()
