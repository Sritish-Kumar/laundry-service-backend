from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import DeviceType, VerificationPurpose
from app.core.security import (
    create_access_token,
    create_refresh_token,
    current_utc,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.exceptions.custom_exceptions import AuthenticationError, ConflictError, NotFoundError
from app.models import AuthSession, User
from app.repo.auth_session_repo import AuthSessionRepository
from app.repo.user_repo import UserRepository
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
from app.services.verification_service import VerificationRequest, VerificationService


@dataclass
class SessionMetadata:
    device_name: str | None = None
    device_type: DeviceType = DeviceType.WEB
    user_agent: str | None = None
    ip_address: str | None = None


class AuthService:
    INVALID_AUTH_MESSAGE = "Invalid authentication credentials"
    EMAIL_NOT_VERIFIED_MESSAGE = "Your email is not verified. A new verification code has been sent."
    GENERIC_VERIFICATION_SENT_MESSAGE = (
        "If an account exists and requires verification, a verification code has been sent."
    )
    FORGOT_PASSWORD_SUCCESS_MESSAGE = "If an account exists, a password reset code has been sent."
    SIGNUP_SUCCESS_MESSAGE = "Verification code sent successfully."
    RESET_PASSWORD_SUCCESS_MESSAGE = "Password reset successfully."
    CHANGE_PASSWORD_SUCCESS_MESSAGE = "Password changed successfully."
    CHANGE_EMAIL_SENT_MESSAGE = "Verification code sent to your new email address."
    CHANGE_EMAIL_SUCCESS_MESSAGE = "Email changed successfully."

    @staticmethod
    def signup(
        db: Session,
        signup_data: UserSignupRequest,
    ) -> SignupResponse:
        """Register a new user and send an email verification code."""
        existing_user_by_email = UserRepository.get_user_by_email(db, signup_data.email)
        if existing_user_by_email:
            existing_user_by_phone = UserRepository.get_user_by_phone(db, signup_data.phone)
            if existing_user_by_phone and existing_user_by_phone.id != existing_user_by_email.id:
                raise ConflictError("A user with this phone number already exists")

            if existing_user_by_email.is_email_verified:
                raise ConflictError("A user with this email already exists")

            AuthService._send_signup_verification(db, existing_user_by_email)
            return SignupResponse(
                email=existing_user_by_email.email,
                message=AuthService.SIGNUP_SUCCESS_MESSAGE,
            )

        existing_user_by_phone = UserRepository.get_user_by_phone(db, signup_data.phone)
        if existing_user_by_phone:
            raise ConflictError("A user with this phone number already exists")

        user = User(
            full_name=signup_data.full_name,
            email=signup_data.email,
            phone=signup_data.phone,
            password_hash=hash_password(signup_data.password),
            role=signup_data.role,
            is_email_verified=False,
            email_verified_at=None,
        )

        created_user = UserRepository.create_user(db, user)
        AuthService._send_signup_verification(db, created_user)

        return SignupResponse(
            email=created_user.email,
            message=AuthService.SIGNUP_SUCCESS_MESSAGE,
        )

    @staticmethod
    def login(
        db: Session,
        login_data: UserLoginRequest,
        metadata: SessionMetadata
    ) -> TokenResponse:
        """Validate credentials and issue authentication tokens."""
        user = UserRepository.get_user_by_email(db, login_data.email)

        if not user or not verify_password(login_data.password, user.password_hash):
            raise AuthenticationError(AuthService.INVALID_AUTH_MESSAGE)

        if not user.is_email_verified:
            try:
                VerificationService.resend(
                    db,
                    AuthService._build_verification_request(user),
                )
            except ConflictError:
                pass

            raise AuthenticationError(AuthService.EMAIL_NOT_VERIFIED_MESSAGE)

        return AuthService._issue_tokens(db, user, metadata)

    @staticmethod
    def resend_verification(
        db: Session,
        resend_data: ResendVerificationRequest,
    ) -> None:
        """Send a verification code when the account exists and is still unverified."""
        user = UserRepository.get_user_by_email(db, resend_data.email)
        if not user or user.is_email_verified:
            return

        try:
            VerificationService.resend(
                db,
                AuthService._build_verification_request(user),
            )
        except ConflictError:
            return

    @staticmethod
    def verify_email(
        db: Session,
        verify_data: VerifyEmailRequest,
    ) -> None:
        """Verify a user with a valid OTP and mark their email as confirmed."""
        existing_user = UserRepository.get_user_by_email(db, verify_data.email)
        if existing_user and existing_user.is_email_verified:
            raise ConflictError("Email is already verified")

        verified_user = VerificationService.verify(
            db,
            verify_data.email,
            verify_data.otp,
            VerificationPurpose.EMAIL_VERIFICATION,
        )

        if verified_user.is_email_verified:
            raise ConflictError("Email is already verified")

        UserRepository.update_user(
            db,
            verified_user,
            {
                "is_email_verified": True,
                "email_verified_at": current_utc(),
            },
        )

    @staticmethod
    def forgot_password(db: Session, forgot_data: ForgotPasswordRequest) -> None:
        """Send a password reset OTP to an existing account without revealing account state."""
        user = UserRepository.get_user_by_email(db, forgot_data.email)
        if not user:
            return

        VerificationService.send_verification(
            db,
            AuthService._build_verification_request(
                user,
                identifier=user.email,
                purpose=VerificationPurpose.PASSWORD_RESET,
            ),
        )

    @staticmethod
    def reset_password(db: Session, reset_data: ResetPasswordRequest) -> None:
        """Verify a password reset OTP and replace the account password."""
        verified_user = VerificationService.verify(
            db,
            reset_data.email,
            reset_data.otp,
            VerificationPurpose.PASSWORD_RESET,
        )

        UserRepository.update_user(
            db,
            verified_user,
            {"password_hash": hash_password(reset_data.new_password)},
        )
        AuthService.logout_all(db, verified_user)

    @staticmethod
    def change_password(
        db: Session,
        user: User,
        change_data: ChangePasswordRequest,
    ) -> None:
        """Change the currently authenticated user's password and revoke every session."""
        if not verify_password(change_data.current_password, user.password_hash):
            raise AuthenticationError("Invalid current password")

        UserRepository.update_user(
            db,
            user,
            {"password_hash": hash_password(change_data.new_password)},
        )
        AuthService.logout_all(db, user)

    @staticmethod
    def change_email(
        db: Session,
        user: User,
        change_data: ChangeEmailRequest,
    ) -> None:
        """Send an email change OTP to the requested new address."""
        existing_user = UserRepository.get_user_by_email(db, change_data.new_email)
        if existing_user and existing_user.id != user.id:
            raise ConflictError("A user with this email already exists")

        VerificationService.send_verification(
            db,
            AuthService._build_verification_request(
                user,
                identifier=change_data.new_email,
                purpose=VerificationPurpose.EMAIL_CHANGE,
            ),
        )

    @staticmethod
    def confirm_change_email(
        db: Session,
        user: User,
        confirm_data: ConfirmEmailChangeRequest,
    ) -> None:
        """Verify an email change OTP and update the authenticated user's email."""
        existing_user = UserRepository.get_user_by_email(db, confirm_data.new_email)
        if existing_user and existing_user.id != user.id:
            raise ConflictError("A user with this email already exists")

        verified_user = VerificationService.verify(
            db,
            confirm_data.new_email,
            confirm_data.otp,
            VerificationPurpose.EMAIL_CHANGE,
        )

        UserRepository.update_user(
            db,
            verified_user,
            {
                "email": confirm_data.new_email,
                "is_email_verified": True,
                "email_verified_at": current_utc(),
            },
        )

    @staticmethod
    def refresh(db: Session, refresh_data: RefreshTokenRequest) -> TokenResponse:
        """Issue a new access token for an active refresh-token session."""
        auth_session = AuthService._get_active_session_from_refresh_token(
            db,
            refresh_data.refresh_token,
        )
        if not auth_session.user:
            raise AuthenticationError(AuthService.INVALID_AUTH_MESSAGE)

        issued_at = current_utc()
        refresh_expires_at = issued_at + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = create_refresh_token(
            user_id=auth_session.user.id,
            session_id=auth_session.id,
        )

        AuthSessionRepository.update_session(
            db,
            auth_session,
            {
                "refresh_token_hash": hash_refresh_token(new_refresh_token),
                "expires_at": refresh_expires_at,
                "last_used_at": issued_at,
            },
        )

        access_token = create_access_token(
            user_id=auth_session.user.id,
            role=auth_session.user.role,
            session_id=auth_session.id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def logout(db: Session, refresh_data: RefreshTokenRequest) -> None:
        """Revoke the active session identified by a refresh token."""
        auth_session = AuthService._get_active_session_from_refresh_token(
            db,
            refresh_data.refresh_token,
        )

        AuthSessionRepository.update_session(
            db,
            auth_session,
            {"revoked_at": current_utc()},
        )

    @staticmethod
    def logout_all(db: Session, user: User) -> None:
        """Revoke all active sessions for a user."""
        AuthSessionRepository.revoke_all_sessions(db, user.id)

    @staticmethod
    def get_sessions(
        db: Session,
        user: User,
        current_session_id: uuid.UUID,
    ) -> list[AuthSessionResponse]:
        sessions = AuthSessionRepository.get_user_sessions(db, user.id)
        return [
            AuthSessionResponse(
                id=str(session.id),
                device_name=session.device_name,
                device_type=session.device_type,
                last_used_at=session.last_used_at,
                created_at=session.created_at,
                current=session.id == current_session_id,
            )
            for session in sessions
        ]

    @staticmethod
    def revoke_session(db: Session, user: User, session_id: uuid.UUID) -> None:
        auth_session = AuthSessionRepository.get_active_user_session(
            db,
            session_id,
            user.id,
        )
        if not auth_session:
            raise NotFoundError("Session not found")

        AuthSessionRepository.update_session(
            db,
            auth_session,
            {"revoked_at": current_utc()},
        )

    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        return AuthSessionRepository.cleanup_expired_sessions(db)

    @staticmethod
    def cleanup_revoked_sessions(db: Session) -> int:
        return AuthSessionRepository.cleanup_revoked_sessions(db)

    @staticmethod
    def _get_active_session_from_refresh_token(
        db: Session,
        refresh_token: str
    ) -> AuthSession:
        try:
            payload = decode_refresh_token(refresh_token)
            session_id = uuid.UUID(str(payload.get("sid")))
        except (AuthenticationError, TypeError, ValueError) as exc:
            raise AuthenticationError(AuthService.INVALID_AUTH_MESSAGE) from exc

        auth_session = AuthSessionRepository.get_active_session_by_hash(
            db,
            hash_refresh_token(refresh_token),
        )

        if not auth_session or auth_session.id != session_id:
            raise AuthenticationError(AuthService.INVALID_AUTH_MESSAGE)

        return auth_session

    @staticmethod
    def _issue_tokens(
        db: Session,
        user: User,
        metadata: SessionMetadata
    ) -> TokenResponse:
        """Generate access and refresh tokens, store session state, and return token data."""
        session_id = uuid.uuid4()
        issued_at = current_utc()
        refresh_expires_at = issued_at + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_token = create_refresh_token(user_id=user.id, session_id=session_id)
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            session_id=session_id,
        )

        auth_session = AuthService._create_session(
            user=user,
            session_id=session_id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            issued_at=issued_at,
            expires_at=refresh_expires_at,
            metadata=metadata,
        )

        AuthSessionRepository.create_session(db, auth_session)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def _create_session(
        *,
        user: User,
        session_id: uuid.UUID,
        refresh_token_hash: str,
        issued_at: datetime,
        expires_at: datetime,
        metadata: SessionMetadata
    ) -> AuthSession:
        """Build a refresh-token session record for the authenticated user."""
        return AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            device_name=metadata.device_name,
            device_type=metadata.device_type,
            user_agent=metadata.user_agent,
            ip_address=metadata.ip_address,
            last_used_at=issued_at,
            expires_at=expires_at,
            revoked_at=None,
        )

    @staticmethod
    def _build_verification_request(
        user: User,
        *,
        identifier: str | None = None,
        purpose: VerificationPurpose = VerificationPurpose.EMAIL_VERIFICATION,
    ) -> VerificationRequest:
        """Create a verification request for a user with a specific purpose and identifier."""
        return VerificationRequest(
            user=user,
            identifier=identifier or user.email,
            purpose=purpose,
        )

    @staticmethod
    def _send_signup_verification(db: Session, user: User) -> None:
        """Generate and send a verification code for a newly created or reactivated account."""
        VerificationService.send_verification(
            db,
            AuthService._build_verification_request(user),
        )
