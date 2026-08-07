from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from app.core.constants import UserRole
from app.core.constants import DeviceType

class UserSignupRequest(BaseModel):
    full_name: str = Field(
        default=..., min_length=2, max_length=50,
        description="The user's full name.",
        examples=["Jane Doe"]
    )
    email: EmailStr = Field(
        default=..., description="The user's email address.",
        examples=["jane@example.com"]
    )
    phone: str = Field(
        default=..., min_length=10, max_length=15,
        description="Phone number with optional country code.",
        examples=["+15551234567"]
    )
    password: str = Field(
        default=..., min_length=8, max_length=128,
        description="The password for the new account.",
        examples=["StrongP@ssw0rd!"]
    )
    role: UserRole = Field(
        default=..., description="Role assigned to the new user.",
        examples=["CUSTOMER"]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "+15551234567",
                "password": "StrongP@ssw0rd!",
                "role": "CUSTOMER"
            }
        }
    }


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(
        default=..., description="Registered email address.",
        examples=["jane@example.com"]
    )
    password: str = Field(
        default=..., description="User password.",
        examples=["StrongP@ssw0rd!"]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "jane@example.com",
                "password": "StrongP@ssw0rd!"
            }
        }
    }


class TokenResponse(BaseModel):
    access_token: str = Field(default=..., description="JWT access token.")
    refresh_token: str = Field(default=..., description="Refresh token used to obtain new access tokens.")
    expires_in: int = Field(default=..., description="Expiration time in seconds for the access token.", examples=[3600])
    token_type: str = Field(default="bearer", description="Type of the issued token.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "dGhpcy1pcy1hLXJlZnJlc2gtdG9rZW4=",
                "expires_in": 3600,
                "token_type": "bearer"
            }
        }
    }

class SignupResponse(BaseModel):
    email: EmailStr
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "jane@example.com",
                "message": "Verification code sent successfully."
            }
        }
    }

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(
        default=...,
        min_length=6,
        max_length=6,
        description="Six-digit email verification code.",
        examples=["483921"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "jane@example.com",
                "otp": "483921"
            }
        }
    }


class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(
        default=...,
        description="Email address to resend the verification code to.",
        examples=["jane@example.com"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "jane@example.com"
            }
        }
    }


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(
        default=...,
        description="Email address to send a password reset code to.",
        examples=["jane@example.com"],
    )


class ResetPasswordRequest(BaseModel):
    email: EmailStr = Field(
        default=...,
        description="Email address associated with the password reset request.",
        examples=["jane@example.com"],
    )
    otp: str = Field(
        default=...,
        min_length=6,
        max_length=6,
        description="Six-digit password reset code.",
        examples=["483921"],
    )
    new_password: str = Field(
        default=...,
        min_length=8,
        max_length=128,
        description="New password to set for the account.",
        examples=["NewStrongP@ssw0rd!"],
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        default=...,
        description="The current account password.",
        examples=["StrongP@ssw0rd!"],
    )
    new_password: str = Field(
        default=...,
        min_length=8,
        max_length=128,
        description="New password to save for the account.",
        examples=["NewStrongP@ssw0rd!"],
    )


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr = Field(
        default=...,
        description="The new email address to verify and use.",
        examples=["jane.new@example.com"],
    )


class ConfirmEmailChangeRequest(BaseModel):
    new_email: EmailStr = Field(
        default=...,
        description="The new email address that was verified.",
        examples=["jane.new@example.com"],
    )
    otp: str = Field(
        default=...,
        min_length=6,
        max_length=6,
        description="Six-digit verification code sent to the new email address.",
        examples=["654321"],
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(default=..., description="JWT refresh token.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "dGhpcy1pcy1hLXJlZnJlc2gtdG9rZW4="
            }
        }
    }


class AuthSessionResponse(BaseModel):
    id: str
    device_name: str | None
    device_type: DeviceType
    last_used_at: datetime
    created_at: datetime
    current: bool
