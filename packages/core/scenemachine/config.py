"""Application configuration and settings management."""

import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Settings are loaded from environment variables and .env files.
    All settings have sensible defaults for development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SceneMachine"
    version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1

    # Database
    database_url: str = "sqlite:///./data/scenemachine.db"
    database_echo: bool = False

    # Storage paths
    data_dir: Path = Path("./data")
    upload_dir: Path = Field(default=Path("./data/uploads"))
    output_dir: Path = Field(default=Path("./data/outputs"))
    model_cache_dir: Path = Field(default=Path("./data/models"))

    # Security
    secret_key: str = "change-me-in-production-use-strong-random-key"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # AI/ML Configuration
    default_llm_provider: str = "anthropic"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Generation
    default_video_model: str = "local"
    max_concurrent_generations: int = 2
    generation_timeout_seconds: int = 600

    # IPC Configuration
    ipc_socket_path: str = "/tmp/scenemachine.sock"

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("data_dir", "upload_dir", "output_dir", "model_cache_dir", mode="after")
    @classmethod
    def ensure_directory_exists(cls, v: Path) -> Path:
        """Ensure storage directories exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.environment == "testing"

    def configure_logging(self) -> None:
        """Configure application logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format,
        )

        # Reduce noise from third-party libraries
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(
            logging.INFO if self.database_echo else logging.WARNING
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Settings are loaded once and cached for the lifetime of the application.
    Use reset_settings() to clear the cache if needed.
    """
    settings = Settings()
    settings.configure_logging()
    return settings


def reset_settings() -> None:
    """Clear the cached settings.

    Useful for testing or when environment variables change.
    """
    get_settings.cache_clear()
