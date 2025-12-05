from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Project Alpha"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    # Development
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
