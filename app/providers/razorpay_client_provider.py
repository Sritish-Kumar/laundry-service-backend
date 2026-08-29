from typing import Any

import razorpay
from razorpay.errors import SignatureVerificationError

from app.core.config import settings
from app.core.logger import logger
from app.providers.razorpay_provider import RazorpayProvider


class RazorpayClientProvider(RazorpayProvider):

    def __init__(self) -> None:
        self._client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, *, amount: int, currency: str, receipt: str) -> dict[str, Any]:
        return self._client.order.create(  # type: ignore[attr-defined]
            {
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
            }
        )

    def fetch_payment(self, *, payment_id: str) -> dict[str, Any]:
        return self._client.payment.fetch(payment_id)  # type: ignore[attr-defined]

    def verify_payment_signature(self, *, params: dict[str, Any]) -> bool:
        try:
            self._client.utility.verify_payment_signature(params)  # type: ignore[attr-defined]
            return True
        except SignatureVerificationError:
            logger.warning("Razorpay payment signature verification failed. params=%s", params)
            return False

    def verify_webhook_signature(self, *, payload: str, signature: str) -> bool:
        try:
            self._client.utility.verify_webhook_signature(              # type: ignore[attr-defined]
                payload, signature, settings.RAZORPAY_WEBHOOK_SECRET
            )
            return True
        except SignatureVerificationError:
            logger.warning("Razorpay webhook signature verification failed.")
            return False
