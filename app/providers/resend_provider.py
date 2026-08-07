import resend

from app.core.config import settings
from app.core.logger import logger
from app.providers.email_provider import EmailMessage, EmailProvider


class ResendProvider(EmailProvider):

    def send(self, *, email_message: EmailMessage) -> None:
        if not settings.RESEND_API_KEY:
            logger.info(
                "Email delivery skipped; RESEND_API_KEY is not configured. recipient=%s subject=%s",
                email_message.recipient,
                email_message.subject,
            )
            return

        if email_message.recipient.endswith("@example.com") or "example.com" in email_message.recipient:
            logger.info(
                "Email delivery skipped for example.com address. recipient=%s subject=%s",
                email_message.recipient,
                email_message.subject,
            )
            return

        try:
            resend.api_key = settings.RESEND_API_KEY
            response = resend.Emails.send(
                {
                    "from": settings.EMAIL_FROM,
                    "to": [email_message.recipient],
                    "subject": email_message.subject,
                    "html": email_message.html,
                }
            )
        except Exception as exc:
            logger.exception(
                "Failed to send email via Resend provider. recipient=%s subject=%s",
                email_message.recipient,
                email_message.subject,
            )
            raise RuntimeError("Failed to send email via Resend provider") from exc

        message_id = None
        if isinstance(response, dict):
            message_id = response.get("id")
        else:
            message_id = getattr(response, "id", None)

        logger.info(
            "Email delivered via Resend provider. recipient=%s message_id=%s response=%s",
            email_message.recipient,
            message_id,
            response,
        )

