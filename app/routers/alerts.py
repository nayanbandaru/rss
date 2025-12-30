from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, validate_email_param
from app.models.requests import AlertCreateRequest
from app.models.responses import (
    AlertResponse,
    AlertListResponse,
    AlertCreateResponse,
    AlertDeleteResponse
)
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/",
             response_model=AlertCreateResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new alert")
async def create_alert(
    request: AlertCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new alert for monitoring Reddit posts.

    - **email**: User's email address (auto-creates user if new)
    - **subreddit**: Subreddit to monitor (e.g., "watchexchange" or "r/watchexchange")
    - **keyword**: Keyword to search for in posts (case-insensitive)

    Returns the created alert with a unique ID.

    Raises:
    - 400: Invalid email format
    - 409: Alert already exists for this subreddit and keyword
    """
    alert = AlertService.create_alert(
        db=db,
        email=request.email,
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
    email: str = Query(..., description="User email address"),
    db: Session = Depends(get_db)
):
    """
    Get all alerts for a specific user email.

    - **email**: User's email address

    Returns a list of alerts with their details.
    Returns an empty list if the user has no alerts or doesn't exist.

    Raises:
    - 400: Invalid email format
    """
    # Validate email format
    email = validate_email_param(email)

    # Get alerts
    alerts = AlertService.list_user_alerts(db, email)

    return AlertListResponse(
        email=email,
        alerts=[AlertResponse.model_validate(a) for a in alerts],
        count=len(alerts)
    )


@router.delete("/{alert_id}",
               response_model=AlertDeleteResponse,
               summary="Delete an alert")
async def delete_alert(
    alert_id: str,
    email: str = Query(..., description="User email for ownership verification"),
    db: Session = Depends(get_db)
):
    """
    Delete a specific alert by ID.

    - **alert_id**: UUID of the alert to delete
    - **email**: User email for ownership verification

    Returns success message if deleted.

    Raises:
    - 400: Invalid email format
    - 403: User doesn't own this alert
    - 404: Alert not found
    """
    deleted_alert = AlertService.delete_alert(db, alert_id, email)

    return AlertDeleteResponse(
        message="Alert deleted successfully",
        deleted_alert_id=deleted_alert.id
    )
