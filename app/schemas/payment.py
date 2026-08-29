from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.core.constants import PaymentMethod, PaymentStatus


class PaymentResponse(BaseModel):

    payment_method: PaymentMethod
    payment_status: PaymentStatus
    amount: Decimal
    currency: str

    model_config = ConfigDict(from_attributes=True)


# Razorpay checkout schemas

class RazorpayCheckoutResponse(BaseModel):
    """Everything the frontend needs to open Razorpay Checkout. Never
    include RAZORPAY_KEY_SECRET or RAZORPAY_WEBHOOK_SECRET here."""

    razorpay_key_id: str
    razorpay_order_id: str
    amount: int
    currency: str


class RazorpayVerifyRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
