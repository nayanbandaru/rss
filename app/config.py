from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "sqlite:///./watch.db"

    # API Settings
    api_v1_prefix: str = "/api/v1"
    app_title: str = "Reddit Alert Monitor"
    app_version: str = "1.0.0"
    app_description: str = "API for managing Reddit alert subscriptions"

    # CORS
    cors_origins: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Rate Limiting
    rate_limit_requests: int = 20  # per minute per IP

    # Future: Authentication (placeholder)
    enable_auth: bool = False
    jwt_secret_key: str = "placeholder-change-in-production"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars (Reddit, Gmail credentials used by poller)


settings = Settings()
