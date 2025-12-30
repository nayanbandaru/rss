from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from email_validator import validate_email, EmailNotValidError

from db import SessionLocal, init_db


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    Automatically handles session cleanup.
    """
    init_db()  # Ensure tables exist
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_email_param(email: str) -> str:
    """
    Validate and normalize email parameter.

    Args:
        email: Email address to validate

    Returns:
        Normalized email address

    Raises:
        HTTPException: If email is invalid
    """
    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email: {str(e)}"
        )


async def get_current_user() -> Optional[dict]:
    """
    Placeholder for future authentication.

    Currently returns None (no auth).
    When authentication is implemented:
    1. Decode JWT token from Authorization header
    2. Validate token
    3. Return user info dict

    Usage in routes:
        current_user: dict = Depends(get_current_user)
    """
    return None  # No auth for now
