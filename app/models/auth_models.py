"""
Authentication request and response models.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Request schema for user registration"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 chars, must include uppercase, lowercase, and digit)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }
    }


class UserLoginRequest(BaseModel):
    """Request schema for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }
    }


class PasswordSetupRequest(BaseModel):
    """Request schema for existing users to set up password"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 chars, must include uppercase, lowercase, and digit)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "existing@example.com",
                "password": "NewSecurePass123"
            }
        }
    }


class PasswordResetRequestModel(BaseModel):
    """Request schema for password reset (request email)"""
    email: EmailStr = Field(..., description="User email address")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com"
            }
        }
    }


class PasswordResetConfirmRequest(BaseModel):
    """Request schema for password reset confirmation"""
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 chars, must include uppercase, lowercase, and digit)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "abc123...",
                "new_password": "NewSecurePass123"
            }
        }
    }


class TokenResponse(BaseModel):
    """Response schema for login/registration"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }
    }


class UserResponse(BaseModel):
    """Response schema for user info"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    is_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    has_password: bool = Field(..., description="Whether user has set up password")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "user@example.com",
                "email": "user@example.com",
                "is_verified": False,
                "created_at": "2024-01-01T00:00:00",
                "has_password": True
            }
        }
    }


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str = Field(..., description="Response message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Operation completed successfully"
            }
        }
    }
