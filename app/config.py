from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "sqlite:///./watch.db"

    # API Settings
    api_v1_prefix: str = "/api/v1"
    app_title: str = "Reddit Alert Monitor"
    app_version: str = "1.0.0"
    app_description: str = "API for managing Reddit alert subscriptions"

    # CORS - can be set via CORS_ORIGINS env var (comma-separated)
    cors_origins: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Rate Limiting
    rate_limit_requests: int = 20  # per minute per IP

    # Authentication
    enable_auth: bool = True
    jwt_secret_key: Optional[str] = None  # REQUIRED in production - set via JWT_SECRET_KEY env var
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours

    # Password Reset
    password_reset_token_expire_hours: int = 24
    password_reset_base_url: str = "http://localhost:8000"  # Set to production URL

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is set in production"""
        if v is None:
            # Check if we're likely in production (no .env file or explicit prod flag)
            if os.environ.get("ENVIRONMENT", "development").lower() == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production. "
                    "Generate one with: openssl rand -hex 32"
                )
            # Use insecure default for development only
            return "dev-secret-key-change-in-production"
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars (Reddit, Gmail credentials used by poller)


settings = Settings()
