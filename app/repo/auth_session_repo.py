from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.models import AuthSession


class AuthSessionRepository:

    @staticmethod
    def create_session(db: Session, auth_session: AuthSession) -> AuthSession:
        db.add(auth_session)
        db.commit()
        db.refresh(auth_session)
        return auth_session

    @staticmethod
    def get_by_id(db: Session, session_id: uuid.UUID) -> AuthSession | None:
        return db.query(AuthSession).filter(AuthSession.id == session_id).first()

    @staticmethod
    def get_by_refresh_hash(db: Session, refresh_token_hash: str) -> AuthSession | None:
        return (
            db.query(AuthSession)
            .filter(AuthSession.refresh_token_hash == refresh_token_hash)
            .first()
        )

    @staticmethod
    def get_active_session_by_hash(db: Session, refresh_token_hash: str) -> AuthSession | None:
        return (
            db.query(AuthSession)
            .filter(
                AuthSession.refresh_token_hash == refresh_token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(UTC)
            )
            .first()
        )

    @staticmethod
    def exists_by_refresh_hash(db: Session, refresh_token_hash: str) -> bool:
        return (
            db.query(AuthSession.id)
            .filter(AuthSession.refresh_token_hash == refresh_token_hash)
            .first()
            is not None
        )

    @staticmethod
    def get_user_sessions(
        db: Session,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 10,
        active_only: bool = True
    ) -> list[AuthSession]:
        query = db.query(AuthSession).filter(AuthSession.user_id == user_id)

        if active_only:
            query = query.filter(
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(UTC)
            )

        return query.order_by(AuthSession.last_used_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_active_user_session(
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AuthSession | None:
        return (
            db.query(AuthSession)
            .filter(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(UTC),
            )
            .first()
        )

    @staticmethod
    def update_session(
        db: Session,
        auth_session: AuthSession,
        update_data: dict[str, Any]
    ) -> AuthSession:
        for field, value in update_data.items():
            if hasattr(auth_session, field):
                setattr(auth_session, field, value)

        db.commit()
        db.refresh(auth_session)
        return auth_session

    @staticmethod
    def revoke_session(db: Session, session_id: uuid.UUID) -> AuthSession | None:
        auth_session = AuthSessionRepository.get_by_id(db, session_id)

        if not auth_session:
            return None

        setattr(auth_session, "revoked_at", datetime.now(UTC))
        db.commit()
        db.refresh(auth_session)
        return auth_session

    @staticmethod
    def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> int:
        revoked_count = (
            db.query(AuthSession)
            .filter(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None)
            )
            .update(
                {AuthSession.revoked_at: datetime.now(UTC)},
                synchronize_session=False
            )
        )
        db.commit()
        return revoked_count

    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        deleted_count = (
            db.query(AuthSession)
            .filter(AuthSession.expires_at < datetime.now(UTC))
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted_count

    @staticmethod
    def cleanup_revoked_sessions(db: Session) -> int:
        deleted_count = (
            db.query(AuthSession)
            .filter(AuthSession.revoked_at.is_not(None))
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted_count

    delete_expired_sessions = cleanup_expired_sessions
    delete_revoked_sessions = cleanup_revoked_sessions
