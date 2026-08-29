import json
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import OrderStatus, PaymentMethod, PaymentStatus, UserRole
from app.core.logger import logger
from app.exceptions.custom_exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models.user import User
from app.repo.order_repo import OrderRepository
from app.repo.payment_repo import PaymentRepository
from app.schemas.payment import PaymentResponse, RazorpayCheckoutResponse, RazorpayVerifyRequest
from app.services.razorpay_service import RazorpayService
from app.services.razorpay_webhook_handlers import RAZORPAY_WEBHOOK_HANDLERS


class PaymentService:

    @staticmethod
    def _get_owned_order(db: Session, order_id: uuid.UUID, user: User):
        order = OrderRepository.get_order_by_id(db, order_id)

        # Same 404 whether the order doesn't exist or belongs to someone
        # else — never reveal that another customer's order exists.
        if order is None or order.user_id != user.id:
            raise NotFoundError("Order not found")

        return order

    @staticmethod
    def start_checkout(db: Session, order_id: uuid.UUID, user: User) -> RazorpayCheckoutResponse:
        order = PaymentService._get_owned_order(db, order_id, user)

        payment = PaymentRepository.get_by_order_id(db, order.id)

        if payment is None:
            raise NotFoundError("Payment not found for this order")

        if payment.payment_method != PaymentMethod.RAZORPAY:
            raise ConflictError("This order is not set up for online payment")

        if payment.payment_status == PaymentStatus.PAID:
            raise ConflictError("This order has already been paid for")

        if payment.amount <= 0:
            raise ConflictError("Invalid payment amount")

        try:
            razorpay_order = RazorpayService.create_order(
                amount=payment.amount,
                currency=payment.currency,
                receipt=order.public_order_number,
            )
        except Exception as exc:
            logger.exception("Failed to create Razorpay order for order_id=%s", order.id)
            raise ConflictError("Unable to start payment with Razorpay right now") from exc

        razorpay_order_id = razorpay_order["id"]

        # A retry after a FAILED attempt reuses the same internal Payment
        # row — a fresh Razorpay order replaces the stale one and the
        # payment goes back to PENDING for the new attempt.
        PaymentRepository.update(
            db,
            payment,
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": None,
                "payment_status": PaymentStatus.PENDING,
            },
        )

        return RazorpayCheckoutResponse(
            razorpay_key_id=settings.RAZORPAY_KEY_ID or "",
            razorpay_order_id=razorpay_order_id,
            amount=RazorpayService.to_smallest_currency_unit(payment.amount),
            currency=payment.currency,
        )

    @staticmethod
    def verify_payment(
        db: Session,
        order_id: uuid.UUID,
        user: User,
        verify_request: RazorpayVerifyRequest,
    ) -> PaymentResponse:
        order = PaymentService._get_owned_order(db, order_id, user)

        payment = PaymentRepository.get_by_order_id(db, order.id)

        if payment is None:
            raise NotFoundError("Payment not found for this order")

        if payment.payment_method != PaymentMethod.RAZORPAY:
            raise ConflictError("This order is not set up for online payment")

        # Idempotent: the webhook may have already settled this payment
        # (possibly before this callback even arrives). Report success
        # without re-verifying or re-processing anything.
        if payment.payment_status == PaymentStatus.PAID:
            return PaymentResponse.model_validate(payment)

        # Never trust the razorpay_order_id the frontend sends on its own —
        # it must match the one *we* created and stored for this order.
        if (
            payment.razorpay_order_id is None
            or payment.razorpay_order_id != verify_request.razorpay_order_id
        ):
            raise ValidationError("Razorpay order ID does not match our records")

        signature_valid = RazorpayService.verify_payment_signature(
            razorpay_order_id=verify_request.razorpay_order_id,
            razorpay_payment_id=verify_request.razorpay_payment_id,
            razorpay_signature=verify_request.razorpay_signature,
        )

        if not signature_valid:
            raise ValidationError("Invalid Razorpay payment signature")

        try:
            provider_payment = RazorpayService.fetch_payment(
                payment_id=verify_request.razorpay_payment_id
            )
        except Exception as exc:
            logger.exception(
                "Failed to fetch Razorpay payment payment_id=%s", verify_request.razorpay_payment_id
            )
            raise ValidationError("Unable to verify payment status with Razorpay") from exc

        provider_status = provider_payment.get("status")

        if provider_status == "captured":
            payment = PaymentRepository.update(
                db,
                payment,
                {
                    "payment_status": PaymentStatus.PAID,
                    "razorpay_payment_id": verify_request.razorpay_payment_id,
                },
            )
        elif provider_status == "failed":
            payment = PaymentRepository.update(
                db,
                payment,
                {
                    "payment_status": PaymentStatus.FAILED,
                    "razorpay_payment_id": verify_request.razorpay_payment_id,
                },
            )
        else:
            # e.g. "authorized" but not yet captured — signature is
            # authentic, but we don't have confirmed money movement yet.
            # Leave PENDING; the webhook will finalize once captured.
            logger.info(
                "Razorpay payment %s not yet captured (status=%s); leaving Payment PENDING",
                verify_request.razorpay_payment_id,
                provider_status,
            )

        return PaymentResponse.model_validate(payment)

    @staticmethod
    def handle_webhook(db: Session, raw_body: bytes, signature: str | None) -> None:
        if not signature:
            raise ValidationError("Missing Razorpay webhook signature")

        payload_str = raw_body.decode("utf-8")

        if not RazorpayService.verify_webhook_signature(payload=payload_str, signature=signature):
            raise ValidationError("Invalid Razorpay webhook signature")

        event = json.loads(payload_str)
        event_type = event.get("event")

        handler = RAZORPAY_WEBHOOK_HANDLERS.get(event_type)

        if handler is None:
            logger.info("Unhandled Razorpay webhook event: %s", event_type)
            return

        payment_entity = (
            event.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        handler(db, payment_entity)

    @staticmethod
    def collect_cod_payment(db: Session, order_id: uuid.UUID, user: User) -> PaymentResponse:
        order = OrderRepository.get_order_by_id(db, order_id)

        if order is None:
            raise NotFoundError("Order not found")

        # ADMIN is an operational override (same precedent as
        # OrderService.update_order_status); a DELIVERY_AGENT must be the
        # one actually assigned to this order's delivery.
        if user.role == UserRole.DELIVERY_AGENT and order.delivery_agent_id != user.id:
            raise PermissionDeniedError("You are not the delivery agent assigned to this order.")

        payment = PaymentRepository.get_by_order_id(db, order.id)

        if payment is None:
            raise NotFoundError("Payment not found for this order")

        if payment.payment_method != PaymentMethod.COD:
            raise ConflictError("This order is not a COD payment")

        if order.status != OrderStatus.OUT_FOR_DELIVERY:
            raise ConflictError("Order must be out for delivery before COD can be collected")

        # Idempotent: a repeated "Collect" tap must be a safe no-op, not a
        # second financial side effect.
        if payment.payment_status == PaymentStatus.PAID:
            return PaymentResponse.model_validate(payment)

        if payment.payment_status != PaymentStatus.PENDING:
            raise ConflictError(f"Cannot collect COD payment in status {payment.payment_status.value}")

        updated = PaymentRepository.mark_paid_if_pending(db, payment.id)

        if updated is None:
            # Lost a race with a concurrent collection request — the
            # payment is PAID either way, so report that instead of erroring.
            updated = PaymentRepository.get_by_id(db, payment.id)

        return PaymentResponse.model_validate(updated)
