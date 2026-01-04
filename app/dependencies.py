from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from email_validator import validate_email, EmailNotValidError

from db import SessionLocal, init_db, User
from app.utils.security import decode_access_token


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


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Extracts token from Authorization header (format: "Bearer <token>"),
    validates it, and returns the User object.

    Args:
        authorization: Authorization header value
        db: Database session

    Returns:
        User object for authenticated user

    Raises:
        HTTPException 401: If token is missing, invalid, or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization:
        raise credentials_exception

    # Parse "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise credentials_exception

    token = parts[1]

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns User if token is valid, None otherwise.
    Does not raise exceptions for missing/invalid tokens.

    Args:
        authorization: Authorization header value
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not authorization:
        return None

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]
        payload = decode_access_token(token)
        if payload is None:
            return None

        email: str = payload.get("sub")
        if email is None:
            return None

        user = db.query(User).filter(User.email == email).first()
        return user
    except Exception:
        return None
