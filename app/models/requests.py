from pydantic import BaseModel, EmailStr, Field, field_validator


class AlertCreateRequest(BaseModel):
    """Request schema for creating a new alert"""

    email: EmailStr = Field(..., description="User email address")
    subreddit: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Subreddit name (with or without 'r/' prefix)"
    )
    keyword: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Keyword to monitor in posts"
    )

    @field_validator('subreddit')
    @classmethod
    def normalize_subreddit(cls, v: str) -> str:
        """Remove 'r/' prefix and strip whitespace (same as manage.py)"""
        return v.replace("r/", "").strip()

    @field_validator('keyword')
    @classmethod
    def normalize_keyword(cls, v: str) -> str:
        """Strip whitespace from keyword (same as manage.py)"""
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "subreddit": "watchexchange",
                "keyword": "Seiko SARB"
            }
        }
    }
