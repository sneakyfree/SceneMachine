"""
Configuration settings for SceneMachine Network.

Uses pydantic-settings for environment variable management.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SceneMachine Network"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/scenemachine_network",
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # OAuth2 (optional providers)
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None

    # Cloudflare R2 Storage
    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: str = "scenemachine-network"
    r2_public_url: Optional[str] = None

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_connect_client_id: Optional[str] = None

    # Email (for verification, notifications)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: str = "noreply@scenemachine.network"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 60

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "https://scenemachine.network"],
        description="Allowed CORS origins",
    )

    # Studio Integration
    studio_api_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
