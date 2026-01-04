"""
Authentication router - handles user registration, login, and password management.
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.auth_models import (
    UserRegisterRequest,
    UserLoginRequest,
    PasswordSetupRequest,
    PasswordResetRequestModel,
    PasswordResetConfirmRequest,
    TokenResponse,
    UserResponse,
    MessageResponse
)
from app.services.auth_service import AuthService
from app.middleware.rate_limiter import limiter
from app.config import settings
from db import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register",
             response_model=TokenResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Register new user")
@limiter.limit("3/minute")
async def register(
    request: Request,
    data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email and password.

    - **email**: Valid email address
    - **password**: Minimum 8 characters, must include uppercase, lowercase, and digit

    Returns JWT access token for immediate authentication.

    Raises:
    - 400: Invalid password or user already exists with password
    """
    user, access_token = AuthService.register_user(
        db=db,
        email=data.email,
        password=data.password
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/login",
             response_model=TokenResponse,
             summary="Login user")
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and receive JWT token.

    - **email**: User's email address
    - **password**: User's password

    Returns JWT access token.

    Raises:
    - 401: Invalid credentials
    - 403: User exists but has no password (needs password setup)
    """
    user, access_token = AuthService.login_user(
        db=db,
        email=data.email,
        password=data.password
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/setup-password",
             response_model=TokenResponse,
             summary="Set up password for existing user")
@limiter.limit("3/minute")
async def setup_password(
    request: Request,
    data: PasswordSetupRequest,
    db: Session = Depends(get_db)
):
    """
    Set up password for existing users who don't have one yet.

    This is for users created before authentication was added.

    - **email**: Existing user's email address
    - **password**: New password (min 8 chars, uppercase, lowercase, digit)

    Returns JWT access token after password is set.

    Raises:
    - 400: Invalid password or password already set
    - 404: User not found
    """
    user, access_token = AuthService.setup_password(
        db=db,
        email=data.email,
        password=data.password
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/forgot-password",
             response_model=MessageResponse,
             summary="Request password reset")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: PasswordResetRequestModel,
    db: Session = Depends(get_db)
):
    """
    Request password reset email.

    - **email**: User's email address

    Sends password reset email if user exists and has password.
    Always returns success (doesn't reveal if user exists).

    Reset link is valid for 24 hours.
    """
    AuthService.request_password_reset(db=db, email=data.email)

    return MessageResponse(
        message="If the email exists, a password reset link has been sent."
    )


@router.post("/reset-password",
             response_model=MessageResponse,
             summary="Reset password with token")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    data: PasswordResetConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using token from email.

    - **token**: Reset token from email
    - **new_password**: New password (min 8 chars, uppercase, lowercase, digit)

    Raises:
    - 400: Invalid/expired token or invalid password
    """
    AuthService.reset_password(
        db=db,
        token=data.token,
        new_password=data.new_password
    )

    return MessageResponse(
        message="Password reset successfully. Please log in with your new password."
    )


@router.get("/me",
            response_model=UserResponse,
            summary="Get current user info")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get authenticated user's information.

    **Requires authentication** - include JWT token in Authorization header.

    Returns user details including email, verification status, etc.

    Raises:
    - 401: Invalid or missing token
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        has_password=bool(current_user.password_hash)
    )
