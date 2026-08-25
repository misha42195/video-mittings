from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/video_meetings"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60
    cors_allow_origins: list[str] = ["http://localhost:3000"]
    storage_root: Path = Path(__file__).resolve().parents[2] / "storage"
    max_file_size: int = 100 * 1024 * 1024
    allowed_extensions: set[str] = {".mp4", ".mov", ".wav", ".mp3", ".pdf", ".docx"}
    allowed_content_types: set[str] = {
        "video/mp4",
        "video/quicktime",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
