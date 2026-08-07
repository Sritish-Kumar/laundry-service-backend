from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import VerificationPurpose
from app.core.otp import generate_otp, hash_otp, verify_otp
from app.core.security import current_utc
from app.exceptions.custom_exceptions import AuthenticationError, ConflictError
from app.models import User, Verification
from app.repo.verification_repo import VerificationRepository
from app.services.email_service import EmailService


@dataclass
class VerificationRequest:
    user: User
    identifier: str
    purpose: VerificationPurpose


class VerificationService:
    INVALID_VERIFICATION_MESSAGE = "Invalid or expired verification code"
    RESEND_COOLDOWN_MESSAGE = "Please wait before requesting another verification code"

    @staticmethod
    def send_verification(
        db: Session,
        request: VerificationRequest,
    ) -> Verification:
        active_verification = VerificationRepository.get_active_verification(
            db,
            request.identifier,
            request.purpose,
        )
        if active_verification:
            VerificationRepository.invalidate_active_verification(
                db,
                request.identifier,
                request.purpose,
            )

        otp = generate_otp()
        verification = VerificationService._create_verification(request, otp)
        created_verification = VerificationRepository.create_verification(db, verification)
        VerificationService._send_email(request, otp)
        return created_verification

    @staticmethod
    def verify(
        db: Session,
        identifier: str,
        otp: str,
        purpose: VerificationPurpose,
    ) -> User:
        verification = VerificationRepository.get_active_verification(
            db,
            identifier,
            purpose,
        )
        if not verification:
            raise AuthenticationError(VerificationService.INVALID_VERIFICATION_MESSAGE)

        if verification.failed_attempts >= settings.OTP_MAX_FAILED_ATTEMPTS:
            VerificationRepository.update_verification(
                db,
                verification,
                {"invalidated_at": current_utc()},
            )
            raise AuthenticationError(VerificationService.INVALID_VERIFICATION_MESSAGE)

        if not verify_otp(otp, verification.token_hash):
            updated_verification = VerificationRepository.increment_failed_attempts(
                db,
                verification,
            )
            if updated_verification.failed_attempts >= settings.OTP_MAX_FAILED_ATTEMPTS:
                VerificationRepository.update_verification(
                    db,
                    updated_verification,
                    {"invalidated_at": current_utc()},
                )
            raise AuthenticationError(VerificationService.INVALID_VERIFICATION_MESSAGE)

        if not verification.user:
            raise AuthenticationError(VerificationService.INVALID_VERIFICATION_MESSAGE)

        verified_user = verification.user
        VerificationRepository.mark_used(db, verification)
        return verified_user

    @staticmethod
    def resend(
        db: Session,
        request: VerificationRequest,
    ) -> Verification:
        active_verification = VerificationRepository.get_active_verification(
            db,
            request.identifier,
            request.purpose,
        )
        if active_verification:
            cooldown_until = VerificationService._as_utc(active_verification.created_at) + timedelta(
                seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
            )
            if cooldown_until > current_utc():
                raise ConflictError(VerificationService.RESEND_COOLDOWN_MESSAGE)

        return VerificationService.send_verification(db, request)

    @staticmethod
    def cleanup(db: Session) -> int:
        return VerificationRepository.delete_expired_verifications(db)

    @staticmethod
    def _create_verification(
        request: VerificationRequest,
        otp: str,
    ) -> Verification:
        return Verification(
            user_id=request.user.id,
            identifier=request.identifier,
            purpose=request.purpose,
            token_hash=hash_otp(otp),
            failed_attempts=0,
            expires_at=current_utc() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        )

    @staticmethod
    def _send_email(
        request: VerificationRequest,
        otp: str,
    ) -> None:
        EmailService.send_verification_email(
            recipient=request.identifier,
            purpose=request.purpose,
            otp=otp,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)
