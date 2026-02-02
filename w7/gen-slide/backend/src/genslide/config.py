"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    host: str = "0.0.0.0"
    port: int = 3003

    # Storage configuration
    data_dir: str = "./data"
    slides_dir: str = "./data/slides"
    images_dir: str = "./data/images"

    # AI configuration (OpenRouter)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    image_model: str = "google/gemini-2.5-flash-image-preview:free"
    image_aspect_ratio: str = "16:9"

    # Cost configuration (USD per image)
    style_image_cost: float = 0.02
    slide_image_cost: float = 0.02

    # Polling configuration
    task_poll_interval: int = 1000  # milliseconds
    task_timeout: int = 60000  # milliseconds

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def data_path(self) -> Path:
        """Get the data directory path."""
        return Path(self.data_dir)

    @property
    def slides_path(self) -> Path:
        """Get the slides directory path."""
        return Path(self.slides_dir)

    @property
    def images_path(self) -> Path:
        """Get the images directory path."""
        return Path(self.images_dir)


settings = Settings()
