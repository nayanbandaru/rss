import uuid
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from email_validator import validate_email, EmailNotValidError

from db import User, Alert


class AlertService:
    """
    Service layer for alert operations.
    Adapts existing manage.py business logic for FastAPI.
    """

    @staticmethod
    def get_or_create_user(db: Session, email: str) -> User:
        """
        Get existing user or create new one.
        Adapted from manage.py add_user().

        Args:
            db: Database session
            email: User email address

        Returns:
            User object

        Raises:
            HTTPException: If email is invalid
        """
        # Validate email (same as manage.py)
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email: {str(e)}"
            )

        # Get or create user (same logic as manage.py)
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(id=email, email=email)  # email as ID (MVP pattern)
            db.add(user)
            db.commit()
            db.refresh(user)

        return user

    @staticmethod
    def create_alert(
        db: Session,
        email: str,
        subreddit: str,
        keyword: str
    ) -> Alert:
        """
        Create a new alert.
        Adapted from manage.py add_alert().

        Args:
            db: Database session
            email: User email
            subreddit: Subreddit to monitor (already normalized by Pydantic)
            keyword: Keyword to search (already normalized by Pydantic)

        Returns:
            Created alert object

        Raises:
            HTTPException: If alert already exists or user invalid
        """
        # Normalize inputs (same as manage.py lines 24-25)
        # Note: Pydantic validators already handle this, but we keep for consistency
        subreddit = subreddit.replace("r/", "").strip()
        keyword = keyword.strip()

        # Get or create user
        user = AlertService.get_or_create_user(db, email)

        # Check for duplicate (same as manage.py lines 37-46)
        existing = db.query(Alert).filter(
            Alert.user_id == user.id,
            Alert.subreddit == subreddit,
            Alert.keyword == keyword
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alert already exists for r/{subreddit} with keyword '{keyword}'"
            )

        # Create alert (same as manage.py lines 48-50)
        alert = Alert(
            id=str(uuid.uuid4()),
            user_id=user.id,
            subreddit=subreddit,
            keyword=keyword,
            is_active=True
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        return alert

    @staticmethod
    def list_user_alerts(db: Session, email: str) -> List[Alert]:
        """
        List all alerts for a user.
        Adapted from manage.py list_alerts().

        Args:
            db: Database session
            email: User email

        Returns:
            List of Alert objects (empty if user doesn't exist)
        """
        # Validate email exists (returns empty list if not, same as manage.py)
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return []

        # Get alerts (same as manage.py lines 81-83)
        alerts = db.query(Alert).filter(Alert.user_id == user.id).all()
        return alerts

    @staticmethod
    def delete_alert(db: Session, alert_id: str, email: str) -> Alert:
        """
        Delete an alert.
        Adapted from manage.py delete_alert().

        Args:
            db: Database session
            alert_id: UUID of alert to delete
            email: User email for ownership verification

        Returns:
            Deleted alert object

        Raises:
            HTTPException: If alert not found or user doesn't own it
        """
        # Get alert (same as manage.py line 101)
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Verify ownership (security check - prevents users from deleting others' alerts)
        if alert.user_id != email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own alerts"
            )

        # Delete alert (same as manage.py lines 109-111)
        db.delete(alert)
        db.commit()

        return alert
