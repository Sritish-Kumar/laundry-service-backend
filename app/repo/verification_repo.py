from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import VerificationPurpose
from app.models import Verification


class VerificationRepository:

    @staticmethod
    def create_verification(
        db: Session,
        verification: Verification,
    ) -> Verification:
        db.add(verification)
        db.commit()
        db.refresh(verification)
        return verification

    @staticmethod
    def get_active_verification(
        db: Session,
        identifier: str,
        purpose: VerificationPurpose,
    ) -> Verification | None:
        return (
            db.query(Verification)
            .filter(
                Verification.identifier == identifier,
                Verification.purpose == purpose,
                Verification.used_at.is_(None),
                Verification.invalidated_at.is_(None),
                Verification.expires_at > datetime.now(UTC),
            )
            .first()
        )

    @staticmethod
    def update_verification(
        db: Session,
        verification: Verification,
        update_data: dict[str, Any],
    ) -> Verification:
        for field, value in update_data.items():
            if hasattr(verification, field):
                setattr(verification, field, value)

        db.commit()
        db.refresh(verification)
        return verification

    @staticmethod
    def mark_used(
        db: Session,
        verification: Verification,
    ) -> Verification:
        verification.used_at = datetime.now(UTC)
        db.commit()
        db.refresh(verification)
        return verification

    @staticmethod
    def invalidate_active_verification(
        db: Session,
        identifier: str,
        purpose: VerificationPurpose,
    ) -> int:
        invalidated_count = (
            db.query(Verification)
            .filter(
                Verification.identifier == identifier,
                Verification.purpose == purpose,
                Verification.used_at.is_(None),
                Verification.invalidated_at.is_(None),
                Verification.expires_at > datetime.now(UTC),
            )
            .update(
                {Verification.invalidated_at: datetime.now(UTC)},
                synchronize_session=False,
            )
        )
        db.commit()
        return invalidated_count

    @staticmethod
    def increment_failed_attempts(
        db: Session,
        verification: Verification,
    ) -> Verification:
        verification.failed_attempts += 1
        db.commit()
        db.refresh(verification)
        return verification

    @staticmethod
    def delete_expired_verifications(db: Session) -> int:
        deleted_count = (
            db.query(Verification)
            .filter(Verification.expires_at < datetime.now(UTC))
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted_count
