from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import DeviceType
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
from app.schemas.auth import AuthSessionResponse, RefreshTokenRequest, TokenResponse, UserLoginRequest, UserSignupRequest


@dataclass
class SessionMetadata:
    device_name: str | None = None
    device_type: DeviceType = DeviceType.WEB
    user_agent: str | None = None
    ip_address: str | None = None


class AuthService:
    INVALID_AUTH_MESSAGE = "Invalid authentication credentials"

    @staticmethod
    def signup(
        db: Session,
        signup_data: UserSignupRequest,
        metadata: SessionMetadata
    ) -> TokenResponse:
        """Register a new user and issue authentication tokens."""
        existing_user_by_email = UserRepository.get_user_by_email(db, signup_data.email)
        if existing_user_by_email:
            raise ConflictError("A user with this email already exists")

        existing_user_by_phone = UserRepository.get_user_by_phone(db, signup_data.phone)
        if existing_user_by_phone:
            raise ConflictError("A user with this phone number already exists")

        user = User(
            full_name=signup_data.full_name,
            email=signup_data.email,
            phone=signup_data.phone,
            password_hash=hash_password(signup_data.password),
            role=signup_data.role,
        )

        created_user = UserRepository.create_user(db, user)

        return AuthService._issue_tokens(db, created_user, metadata)

    @staticmethod
    def login(
        db: Session,
        login_data: UserLoginRequest,
        metadata: SessionMetadata
    ) -> TokenResponse:
        """Validate credentials and issue authentication tokens."""
        user = UserRepository.get_user_by_email(db, login_data.email)

        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(login_data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        return AuthService._issue_tokens(db, user, metadata)

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
