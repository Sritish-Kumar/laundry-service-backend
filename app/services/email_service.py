import re
from pathlib import Path

from app.core.config import settings
from app.core.constants import VerificationPurpose
from app.core.email import get_email_provider
from app.providers.email_provider import EmailMessage


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"


class EmailService:
    provider = get_email_provider()

    @staticmethod
    def send(
        *,
        recipient: str,
        subject: str,
        html: str,
    ) -> None:
        EmailService.provider.send(
            email_message=EmailMessage(
                recipient=recipient,
                subject=subject,
                html=html,
            )
        )

    @staticmethod
    def send_verification_email(
        *,
        recipient: str,
        purpose: VerificationPurpose,
        otp: str,
    ) -> None:
        subject = EmailService._verification_subject(purpose)
        template_name = EmailService._template_name(purpose)
        template_path = TEMPLATES_DIR / template_name
        template_html = template_path.read_text(encoding="utf-8")
        html = re.sub(
            r"\{\{\s*(otp|expiry_minutes)\s*\}\}",
            lambda match: str(otp if match.group(1) == "otp" else settings.OTP_EXPIRY_MINUTES),
            template_html,
        )

        EmailService.send(
            recipient=recipient,
            subject=subject,
            html=html,
        )

    @staticmethod
    def _verification_subject(purpose: VerificationPurpose) -> str:
        purpose_label = purpose.value.replace("_", " ").title()
        return f"{purpose_label} code"

    @staticmethod
    def _template_name(purpose: VerificationPurpose) -> str:
        if purpose == VerificationPurpose.PASSWORD_RESET:
            return "password_reset.html"
        if purpose == VerificationPurpose.EMAIL_CHANGE:
            return "email_change.html"
        return "verification.html"
