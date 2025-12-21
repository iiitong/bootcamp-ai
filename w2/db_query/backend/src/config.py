"""Configuration management for DB Query Tool."""

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Supports loading from .env files and environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI API configuration (supports OpenAI-compatible APIs like Amazon Bedrock)
    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Data directory for SQLite storage
    data_dir: Path = Field(
        default=Path.home() / ".db_query",
        validation_alias="DB_QUERY_DATA_DIR",
    )

    # Query settings
    default_query_limit: int = Field(
        default=1000,
        validation_alias="DB_QUERY_DEFAULT_LIMIT",
    )
    query_timeout_seconds: int = Field(
        default=30,
        validation_alias="DB_QUERY_TIMEOUT",
    )

    # CORS settings - stored as comma-separated string for env var compatibility
    cors_origins_str: str = Field(
        default="http://localhost:5173,http://localhost:5174",
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    @model_validator(mode="after")
    def ensure_data_dir_exists(self) -> Self:
        """Ensure the data directory exists after settings are loaded."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self

    @computed_field
    @property
    def db_path(self) -> Path:
        """SQLite database path derived from data_dir."""
        return self.data_dir / "db_query.db"

    @property
    def cors_allowed_origins(self) -> list[str]:
        """CORS allowed origins as a list."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
