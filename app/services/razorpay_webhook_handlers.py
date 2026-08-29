"""Razorpay webhook event handlers.

Kept as a name -> handler map (rather than an if/elif chain in the router
or service) so supporting a new event is just adding one function and one
entry, per the Part 2 plan's extensibility requirement.

Every handler must be idempotent: Razorpay retries webhook delivery, and
the browser-callback verification flow (PaymentService.verify_payment) can
race with the webhook for the same payment. A payment that's already PAID
(or REFUNDED) is left alone, so replays are safe no-ops — but a "captured"
event must still be able to rescue a payment stuck FAILED from an earlier
attempt: Razorpay lets a customer retry within the same order_id, so a
failed first attempt followed by a successful second one is a normal,
expected sequence, not a double-processing case.
"""

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.constants import PaymentStatus
from app.core.logger import logger
from app.repo.payment_repo import PaymentRepository

WebhookHandler = Callable[[Session, dict[str, Any]], None]


def _load_payment_for_entity(db: Session, payment_entity: dict[str, Any]):
    razorpay_order_id = payment_entity.get("order_id")

    if not razorpay_order_id:
        logger.warning("Razorpay webhook payment entity missing order_id: %s", payment_entity)
        return None

    payment = PaymentRepository.get_by_razorpay_order_id(db, razorpay_order_id)

    if payment is None:
        logger.warning("No Payment found for razorpay_order_id=%s", razorpay_order_id)

    return payment


def handle_payment_captured(db: Session, payment_entity: dict[str, Any]) -> None:
    payment = _load_payment_for_entity(db, payment_entity)

    # Only skip if we've already recorded this exact outcome (idempotent
    # replay) or the payment was refunded. Deliberately NOT restricted to
    # PENDING: a payment stuck FAILED from an earlier attempt on the same
    # razorpay_order_id must still be moved to PAID by a later successful
    # retry — that's a normal Razorpay Checkout flow, not a replay.
    if payment is None or payment.payment_status in (
        PaymentStatus.PAID,
        PaymentStatus.REFUNDED,
    ):
        return

    PaymentRepository.update(
        db,
        payment,
        {
            "payment_status": PaymentStatus.PAID,
            "razorpay_payment_id": payment_entity.get("id"),
        },
    )


def handle_payment_failed(db: Session, payment_entity: dict[str, Any]) -> None:
    payment = _load_payment_for_entity(db, payment_entity)

    # Deliberately asymmetric to handle_payment_captured above: a failed
    # attempt must never downgrade a payment that's already PAID (e.g. a
    # stray/late webhook for an earlier failed attempt arriving after a
    # later retry already succeeded) — so this only ever fires from PENDING.
    if payment is None or payment.payment_status != PaymentStatus.PENDING:
        return

    PaymentRepository.update(
        db,
        payment,
        {
            "payment_status": PaymentStatus.FAILED,
            "razorpay_payment_id": payment_entity.get("id"),
        },
    )


RAZORPAY_WEBHOOK_HANDLERS: dict[str, WebhookHandler] = {
    "payment.captured": handle_payment_captured,
    "payment.failed": handle_payment_failed,
}
