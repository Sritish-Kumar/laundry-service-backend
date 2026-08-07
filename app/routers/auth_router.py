import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.constants import DeviceType
from app.dependencies.auth import get_current_session_id, get_current_user
from app.dependencies.database import get_db
from app.models import User
from app.schemas.auth import (
    AuthSessionResponse,
    ChangeEmailRequest,
    ChangePasswordRequest,
    ConfirmEmailChangeRequest,
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SignupResponse,
    TokenResponse,
    UserLoginRequest,
    UserSignupRequest,
    VerifyEmailRequest,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService, SessionMetadata


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=ApiResponse[SignupResponse],
    status_code=201,
    summary="Register a new user",
    description="Create a new user account and send an email verification code.",
    response_description="Created user verification",
    responses={
        400: {"description": "Invalid signup payload."},
        409: {"description": "A user with this email or phone already exists."},
    },
)
def signup(
    signup_data: UserSignupRequest,
    db: Session = Depends(get_db)
):
    """Create a new account and send an email verification code."""
    signup_response = AuthService.signup(db, signup_data)

    return ApiResponse(
        success=True,
        message="Verification code sent successfully.",
        data=signup_response,
    )


@router.post(
    "/verify-email",
    response_model=ApiResponse[None],
    summary="Verify email address",
    description="Verify a user's email address with the OTP sent during signup.",
    response_description="Email verification result",
    responses={
        401: {"description": "Invalid or expired verification code."},
        409: {"description": "Email is already verified."},
    },
)
def verify_email(
    verify_data: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """Verify a user's email address with a six-digit OTP."""
    AuthService.verify_email(db, verify_data)
    return ApiResponse(success=True, message="Email verified successfully.", data=None)


@router.post(
    "/resend-verification",
    response_model=ApiResponse[None],
    summary="Resend verification email",
    description="Send another verification code without revealing whether the account exists.",
    response_description="Verification resend result",
)
def resend_verification(
    resend_data: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    """Send a verification code for an unverified account without leaking account state."""
    AuthService.resend_verification(db, resend_data)
    return ApiResponse(
        success=True,
        message="If an account exists and requires verification, a verification code has been sent.",
        data=None,
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
    """Authenticate an existing user and return auth tokens when the account is verified."""
    token = AuthService.login(db, login_data, _get_session_metadata(request))
    return ApiResponse(success=True, message="Login successful.", data=token)


@router.post(
    "/forgot-password",
    response_model=ApiResponse[None],
    summary="Request a password reset code",
    description="Send a password reset code to an existing account without revealing account state.",
    response_description="Password reset result",
)
def forgot_password(
    forgot_data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Send a password reset OTP to an existing account without leaking account state."""
    AuthService.forgot_password(db, forgot_data)
    return ApiResponse(
        success=True,
        message="If an account exists, a password reset code has been sent.",
        data=None,
    )


@router.post(
    "/reset-password",
    response_model=ApiResponse[None],
    summary="Reset a password with an OTP",
    description="Verify a password reset code and replace the user's password.",
    response_description="Password reset result",
    responses={
        401: {"description": "Invalid or expired password reset code."},
    },
)
def reset_password(
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Verify a password reset OTP and replace the account password."""
    AuthService.reset_password(db, reset_data)
    return ApiResponse(success=True, message="Password reset successfully.", data=None)


@router.post(
    "/change-password",
    response_model=ApiResponse[None],
    summary="Change the current user's password",
    description="Update the authenticated user's password and revoke all existing sessions.",
    response_description="Password change result",
    responses={
        401: {"description": "Invalid current password."},
    },
)
def change_password(
    change_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the authenticated user's password and revoke every active session."""
    AuthService.change_password(db, current_user, change_data)
    return ApiResponse(success=True, message="Password changed successfully.", data=None)


@router.post(
    "/change-email",
    response_model=ApiResponse[None],
    summary="Request an email change",
    description="Send a verification code to the new email address for an authenticated user.",
    response_description="Email change result",
)
def change_email(
    change_data: ChangeEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a verification code to a new email address for the authenticated user."""
    AuthService.change_email(db, current_user, change_data)
    return ApiResponse(
        success=True,
        message="Verification code sent to your new email address.",
        data=None,
    )


@router.post(
    "/confirm-change-email",
    response_model=ApiResponse[None],
    summary="Confirm an email change",
    description="Verify the OTP sent to the new email address and update the account email.",
    response_description="Email change confirmation result",
    responses={
        401: {"description": "Invalid or expired verification code."},
    },
)
def confirm_change_email(
    confirm_data: ConfirmEmailChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify a new-email OTP and update the authenticated user's email address."""
    AuthService.confirm_change_email(db, current_user, confirm_data)
    return ApiResponse(success=True, message="Email changed successfully.", data=None)


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
    response_model=TokenResponse,
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
    return AuthService.login(db, login_data, _get_session_metadata(request))


def _get_session_metadata(request: Request) -> SessionMetadata:
    """Build request metadata for auth sessions from the incoming FastAPI request."""
    return SessionMetadata(
        device_name=None,
        device_type=DeviceType.WEB,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
