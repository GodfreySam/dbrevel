"""User models for authentication and tenant management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class User(BaseModel):
    """User model stored in database."""

    id: str
    email: EmailStr
    password_hash: str
    account_id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool = False
    role: str = "user"  # "user" or "admin"

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "user_1",
                "email": "user@example.com",
                "account_id": "acc_1",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    }


class UserCreate(BaseModel):
    """Request model for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8,
                          description="Password (min 8 characters)")
    name: str = Field(..., description="Account/organization name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "name": "Acme Corp",
            }
        }
    }


class UserLogin(BaseModel):
    """Request model for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            }
        }
    }


class PasswordResetRequest(BaseModel):
    """Request model for password reset request."""

    email: EmailStr = Field(..., description="User email address")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
            }
        }
    }


class PasswordReset(BaseModel):
    """Request model for password reset with OTP."""

    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., description="6-digit OTP code")
    new_password: str = Field(..., min_length=8,
                              description="New password (min 8 characters)")

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        """Strip whitespace and validate OTP format."""
        if not v:
            raise ValueError("OTP is required")
        v = v.strip()
        if len(v) != 6 or not v.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "newsecurepassword123",
            }
        }
    }


class PasswordChange(BaseModel):
    """Request model for changing password (when logged in)."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8,
                              description="New password (min 8 characters)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword123",
            }
        }
    }


class UserResponse(BaseModel):
    """Response model for user information."""

    id: str
    email: EmailStr
    account_id: str
    account_name: str
    projects_count: Optional[int] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool = False
    role: str = "user"  # "user" or "admin"

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "user_1",
                "email": "user@example.com",
                "account_id": "acc_1",
                "account_name": "Acme Corp",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    }


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "user_1",
                    "email": "user@example.com",
                    "account_id": "acc_1",
                },
            }
        }
    }


class PasswordResetResponse(BaseModel):
    """Response model for password reset request."""

    message: str = "If an account with that email exists, a password reset link has been sent."

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "If an account with that email exists, a password reset link has been sent.",
            }
        }
    }


class EmailVerificationRequest(BaseModel):
    """Request model for email verification with OTP."""

    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., description="6-digit OTP code")

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        """Strip whitespace and validate OTP format."""
        if not v:
            raise ValueError("OTP is required")
        v = v.strip()
        if len(v) != 6 or not v.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp": "123456",
            }
        }
    }


class EmailVerificationResponse(BaseModel):
    """Response model for email verification request."""

    message: str = Field(..., description="Response message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Verification email sent. Please check your inbox.",
            }
        }
    }
