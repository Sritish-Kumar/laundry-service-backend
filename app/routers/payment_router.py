import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.roles import require_roles
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.payment import PaymentResponse, RazorpayCheckoutResponse, RazorpayVerifyRequest

from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])

# COD collection is normally the assigned agent's job; ADMIN keeps the same
# operational-override precedent used everywhere else in the order workflow.
_agent_or_admin = require_roles([UserRole.DELIVERY_AGENT, UserRole.ADMIN])


@router.post(
    "/orders/{order_id}/checkout",
    response_model=ApiResponse[RazorpayCheckoutResponse],
)
def start_checkout(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Razorpay order for this order's payment and return what the
    frontend needs to open Razorpay Checkout. Only the order's owner may
    call this, and only for a RAZORPAY payment that isn't already PAID."""
    checkout = PaymentService.start_checkout(db, order_id, current_user)

    return ApiResponse(
        success=True,
        message="Checkout started",
        data=checkout,
    )


@router.post(
    "/orders/{order_id}/verify",
    response_model=ApiResponse[PaymentResponse],
)
def verify_payment(
    order_id: uuid.UUID,
    verify_request: RazorpayVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify a Razorpay Checkout callback against our own stored
    razorpay_order_id and the payment's HMAC signature, then reconcile with
    Razorpay before marking the payment PAID."""
    payment = PaymentService.verify_payment(db, order_id, current_user, verify_request)

    return ApiResponse(
        success=True,
        message="Payment verified",
        data=payment,
    )


@router.post(
    "/orders/{order_id}/cod/collect",
    response_model=ApiResponse[PaymentResponse],
)
def collect_cod_payment(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_agent_or_admin),
):
    """The delivery agent confirms cash was collected on delivery. Only the
    assigned agent (or ADMIN, as an operational override) may call this,
    and only for a COD order that is OUT_FOR_DELIVERY. Safe to call twice —
    an already-PAID payment is returned as-is."""
    payment = PaymentService.collect_cod_payment(db, order_id, current_user)

    return ApiResponse(
        success=True,
        message="COD payment collected",
        data=payment,
    )


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
):
    """Razorpay calls this directly — it is not authenticated with our JWT.
    Authenticity comes solely from X-Razorpay-Signature, verified against
    RAZORPAY_WEBHOOK_SECRET before any event is processed."""
    raw_body = await request.body()

    PaymentService.handle_webhook(db, raw_body, x_razorpay_signature)

    return {"status": "ok"}
