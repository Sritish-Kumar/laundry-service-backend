from decimal import Decimal
from typing import Any

from app.core.razorpay import get_razorpay_provider


class RazorpayService:
    provider = get_razorpay_provider()

    @staticmethod
    def to_smallest_currency_unit(amount: Decimal) -> int:
        return int((amount * 100).to_integral_value())

    @staticmethod
    def create_order(*, amount: Decimal, currency: str, receipt: str) -> dict[str, Any]:
        return RazorpayService.provider.create_order(
            amount=RazorpayService.to_smallest_currency_unit(amount),
            currency=currency,
            receipt=receipt,
        )

    @staticmethod
    def fetch_payment(*, payment_id: str) -> dict[str, Any]:
        return RazorpayService.provider.fetch_payment(payment_id=payment_id)

    @staticmethod
    def verify_payment_signature(
        *,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        return RazorpayService.provider.verify_payment_signature(
            params={
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

    @staticmethod
    def verify_webhook_signature(*, payload: str, signature: str) -> bool:
        return RazorpayService.provider.verify_webhook_signature(
            payload=payload,
            signature=signature,
        )
