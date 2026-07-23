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
