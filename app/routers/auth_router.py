import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.constants import DeviceType
from app.dependencies.auth import get_current_session_id, get_current_user
from app.dependencies.database import get_db
from app.models import User
from app.schemas.auth import AuthSessionResponse, RefreshTokenRequest, TokenResponse, UserLoginRequest, UserSignupRequest
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService, SessionMetadata


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=ApiResponse[TokenResponse],
    status_code=201,
    summary="Register a new user",
    description="Create a new user account and return access and refresh tokens.",
    response_description="Created authentication tokens",
    responses={
        400: {"description": "Invalid signup payload."},
        409: {"description": "A user with this email or phone already exists."},
    },
)
def signup(
    signup_data: UserSignupRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new account and issue authentication tokens."""
    token = AuthService.signup(db, signup_data, _get_session_metadata(request))

    return ApiResponse(
        success=True,
        message="User created successfully.",
        data=token,
    )


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Login with email and password",
    description="Authenticate a user and return access and refresh tokens.",
    response_description="Authentication tokens",
    responses={
        401: {"description": "Invalid email or password."},
    },
)
def login(
    login_data: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate an existing user."""
    token = AuthService.login(db, login_data, _get_session_metadata(request))
    return ApiResponse(success=True, message="Login successful.", data=token)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="Refresh access token",
    description="Return a new access token for an active refresh-token session.",
    response_description="Authentication tokens",
    responses={
        401: {"description": "Invalid refresh token."},
    },
)
def refresh(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh an access token using an active refresh-token session."""
    token = AuthService.refresh(db, refresh_data)
    return ApiResponse(success=True, message="Token refreshed successfully.", data=token)


@router.post(
    "/logout",
    response_model=ApiResponse[None],
    summary="Logout current session",
    description="Revoke the active session identified by a refresh token.",
    response_description="Logout result",
    responses={
        401: {"description": "Invalid refresh token."},
    },
)
def logout(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Revoke the session associated with the provided refresh token."""
    AuthService.logout(db, refresh_data)
    return ApiResponse(success=True, message="Logout successful.", data=None)


@router.post(
    "/logout-all",
    response_model=ApiResponse[None],
    summary="Logout all sessions",
    description="Revoke every active session for the current authenticated user.",
    response_description="Logout all result",
    responses={
        401: {"description": "Invalid access token."},
    },
)
def logout_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke all active sessions for the authenticated user."""
    AuthService.logout_all(db, current_user)
    return ApiResponse(success=True, message="Logged out from all sessions.", data=None)


@router.get(
    "/sessions",
    response_model=ApiResponse[list[AuthSessionResponse]],
    summary="List active sessions",
    description="Return the current user's active authentication sessions.",
    responses={401: {"description": "Invalid access token."}},
)
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_session_id: uuid.UUID = Depends(get_current_session_id),
):
    sessions = AuthService.get_sessions(db, current_user, current_session_id)
    return ApiResponse(success=True, message="Sessions retrieved successfully.", data=sessions)


@router.delete(
    "/sessions/{session_id}",
    response_model=ApiResponse[None],
    summary="Revoke an active session",
    description="Revoke one active authentication session belonging to the current user.",
    responses={
        401: {"description": "Invalid access token."},
        404: {"description": "Session not found."},
    },
)
def revoke_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    AuthService.revoke_session(db, current_user, session_id)
    return ApiResponse(success=True, message="Session revoked successfully.", data=None)


@router.post(
    "/token",
    response_model=ApiResponse[TokenResponse],
    summary="Issue a token with OAuth2 password grant",
    description="Return access and refresh tokens using OAuth2 password form data for Swagger UI.",
    response_description="Authentication tokens",
    responses={
        401: {"description": "Invalid credentials."},
    },
)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 token endpoint for Swagger UI authorization."""
    login_data = UserLoginRequest(email=form_data.username, password=form_data.password)
    token = AuthService.login(db, login_data, _get_session_metadata(request))
    return ApiResponse(success=True, message="Login successful.", data=token)


def _get_session_metadata(request: Request) -> SessionMetadata:
    return SessionMetadata(
        device_name=None,
        device_type=DeviceType.WEB,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
