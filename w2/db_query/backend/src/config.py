"""Configuration management for DB Query Tool."""

import os
from pathlib import Path
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        # OpenAI API configuration (supports OpenAI-compatible APIs like Amazon Bedrock)
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Data directory for SQLite storage
        default_data_dir = Path.home() / ".db_query"
        self.data_dir: Path = Path(os.getenv("DB_QUERY_DATA_DIR", str(default_data_dir)))

        # SQLite database path
        self.db_path: Path = self.data_dir / "db_query.db"

        # Query settings
        self.default_query_limit: int = int(os.getenv("DB_QUERY_DEFAULT_LIMIT", "1000"))
        self.query_timeout_seconds: int = int(os.getenv("DB_QUERY_TIMEOUT", "30"))

        # CORS settings
        # Comma-separated list of allowed origins, or "*" for all (development only)
        cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174")
        self.cors_allowed_origins: list[str] = [
            origin.strip() for origin in cors_origins_str.split(",") if origin.strip()
        ]

    def ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
