from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AlertResponse(BaseModel):
    """Response schema for a single alert"""

    id: str
    user_id: str
    subreddit: str
    keyword: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Enable ORM mode for SQLAlchemy


class AlertListResponse(BaseModel):
    """Response schema for listing alerts"""

    email: str
    alerts: List[AlertResponse]
    count: int


class AlertCreateResponse(BaseModel):
    """Response schema after creating an alert"""

    message: str
    alert: AlertResponse


class AlertDeleteResponse(BaseModel):
    """Response schema after deleting an alert"""

    message: str
    deleted_alert_id: str


class ErrorResponse(BaseModel):
    """Standard error response"""

    detail: str
    error_code: Optional[str] = None
