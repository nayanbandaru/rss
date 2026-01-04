from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.requests import AlertCreateRequest
from app.models.responses import (
    AlertResponse,
    AlertListResponse,
    AlertCreateResponse,
    AlertDeleteResponse
)
from app.services.alert_service import AlertService
from db import User

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/",
             response_model=AlertCreateResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new alert")
async def create_alert(
    request: AlertCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new alert for monitoring Reddit posts.

    **Requires authentication** - include JWT token in Authorization header.

    - **subreddit**: Subreddit to monitor (e.g., "watchexchange" or "r/watchexchange")
    - **keyword**: Keyword to search for in posts (case-insensitive)

    Returns the created alert with a unique ID.

    Raises:
    - 401: Not authenticated
    - 409: Alert already exists for this subreddit and keyword
    """
    alert = AlertService.create_alert(
        db=db,
        email=current_user.email,
        subreddit=request.subreddit,
        keyword=request.keyword
    )

    return AlertCreateResponse(
        message="Alert created successfully",
        alert=AlertResponse.model_validate(alert)
    )


@router.get("/",
            response_model=AlertListResponse,
            summary="List user's alerts")
async def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all alerts for the authenticated user.

    **Requires authentication** - include JWT token in Authorization header.

    Returns a list of alerts with their details.

    Raises:
    - 401: Not authenticated
    """
    alerts = AlertService.list_user_alerts(db, current_user.email)

    return AlertListResponse(
        email=current_user.email,
        alerts=[AlertResponse.model_validate(a) for a in alerts],
        count=len(alerts)
    )


@router.delete("/{alert_id}",
               response_model=AlertDeleteResponse,
               summary="Delete an alert")
async def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific alert by ID.

    **Requires authentication** - include JWT token in Authorization header.

    - **alert_id**: UUID of the alert to delete

    Returns success message if deleted.

    Raises:
    - 401: Not authenticated
    - 403: User doesn't own this alert
    - 404: Alert not found
    """
    deleted_alert = AlertService.delete_alert(db, alert_id, current_user.email)

    return AlertDeleteResponse(
        message="Alert deleted successfully",
        deleted_alert_id=deleted_alert.id
    )
