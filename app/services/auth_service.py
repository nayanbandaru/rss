"""
Service layer for authentication operations.
"""
import uuid
from datetime import datetime, timedelta
from typing import Tuple

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from db import User, PasswordResetToken
from app.utils.security import (
    hash_password,
    verify_password,
    validate_password,
    create_access_token,
    generate_reset_token
)
from app.config import settings
from logger import setup_logger

logger = setup_logger(__name__)


class AuthService:
    """Service layer for authentication operations"""

    @staticmethod
    def register_user(db: Session, email: str, password: str) -> Tuple[User, str]:
        """
        Register a new user with email and password.

        Args:
            db: Database session
            email: User email
            password: Plain text password

        Returns:
            Tuple of (User object, JWT token)

        Raises:
            HTTPException 400: If password is invalid or user already exists with password
        """
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user and existing_user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists. Please log in."
            )

        # If user exists without password (legacy), update them
        if existing_user:
            existing_user.password_hash = hash_password(password)
            existing_user.updated_at = datetime.utcnow()
            user = existing_user
            logger.info(f"Updated existing user with password: {email}")
        else:
            # Create new user
            user = User(
                id=email,  # Keep email as ID for consistency
                email=email,
                password_hash=hash_password(password),
                is_verified=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(user)
            logger.info(f"Created new user: {email}")

        db.commit()
        db.refresh(user)

        # Generate JWT token
        access_token = create_access_token(data={"sub": user.email})

        return user, access_token

    @staticmethod
    def login_user(db: Session, email: str, password: str) -> Tuple[User, str]:
        """
        Authenticate user and generate JWT token.

        Args:
            db: Database session
            email: User email
            password: Plain text password

        Returns:
            Tuple of (User object, JWT token)

        Raises:
            HTTPException 401: If credentials are invalid
            HTTPException 403: If user exists but has no password set
        """
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.warning(f"Login attempt for non-existent user: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if not user.password_hash:
            logger.warning(f"Login attempt for user without password: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please set up your password first. Use the 'Setup Password' option."
            )

        if not verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        logger.info(f"Successful login for user: {email}")

        # Generate JWT token
        access_token = create_access_token(data={"sub": user.email})

        return user, access_token

    @staticmethod
    def setup_password(db: Session, email: str, password: str) -> Tuple[User, str]:
        """
        Set up password for existing user without password (migration path).

        Args:
            db: Database session
            email: User email
            password: Plain text password

        Returns:
            Tuple of (User object, JWT token)

        Raises:
            HTTPException 400: If password invalid or user already has password
            HTTPException 404: If user not found
        """
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please register first."
            )

        if user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password already set. Please use the login option."
            )

        # Set password
        user.password_hash = hash_password(password)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

        logger.info(f"Password set up for existing user: {email}")

        # Generate JWT token
        access_token = create_access_token(data={"sub": user.email})

        return user, access_token

    @staticmethod
    def request_password_reset(db: Session, email: str) -> None:
        """
        Generate password reset token and send email.

        Args:
            db: Database session
            email: User email

        Note:
            Does not raise error if user not found (security - don't leak user existence)
        """
        user = db.query(User).filter(User.email == email).first()

        if not user or not user.password_hash:
            # Don't reveal if user exists or has password
            logger.info(f"Password reset requested for non-existent or passwordless user: {email}")
            return

        # Invalidate any existing unused tokens
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False
        ).update({"used": True})

        # Generate new token
        token = generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(
            hours=settings.password_reset_token_expire_hours
        )

        reset_token = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token=token,
            expires_at=expires_at,
            used=False,
            created_at=datetime.utcnow()
        )
        db.add(reset_token)
        db.commit()

        logger.info(f"Password reset token generated for user: {email}")

        # Send email with reset link
        reset_url = f"{settings.password_reset_base_url}/reset-password?token={token}"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">Password Reset Request</h2>
                <p>You requested to reset your password for Reddit Alert Monitor.</p>
                <p>Click the link below to reset your password (valid for 24 hours):</p>
                <p style="margin: 20px 0;">
                    <a href="{reset_url}"
                       style="background-color: #2563eb; color: white; padding: 10px 20px;
                              text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                </p>
                <p>Or copy this link: {reset_url}</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">
                    If you didn't request this, please ignore this email.
                </p>
            </body>
        </html>
        """

        text_body = f"""
Password Reset Request

You requested to reset your password for Reddit Alert Monitor.

Click the link below to reset your password (valid for 24 hours):
{reset_url}

If you didn't request this, please ignore this email.
        """

        try:
            from emailer import send_email
            send_email(
                to_email=user.email,
                subject="Password Reset - Reddit Alert Monitor",
                html_body=html_body,
                text_body=text_body
            )
            logger.info(f"Password reset email sent to: {email}")
        except Exception as e:
            # Log error but don't expose to user
            logger.error(f"Failed to send password reset email to {email}: {e}")

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> User:
        """
        Reset password using reset token.

        Args:
            db: Database session
            token: Password reset token
            new_password: New plain text password

        Returns:
            Updated User object

        Raises:
            HTTPException 400: If token invalid/expired or password invalid
        """
        # Validate password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Find token
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token
        ).first()

        if not reset_token:
            logger.warning(f"Invalid password reset token attempted")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        if reset_token.used:
            logger.warning(f"Already used password reset token attempted")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has already been used"
            )

        if datetime.utcnow() > reset_token.expires_at:
            logger.warning(f"Expired password reset token attempted")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )

        # Update password
        user = reset_token.user
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()

        # Mark token as used
        reset_token.used = True

        db.commit()
        db.refresh(user)

        logger.info(f"Password reset successful for user: {user.email}")

        return user
