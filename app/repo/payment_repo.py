import uuid
from typing import Any

from sqlalchemy.orm import Session
from app.core.constants import PaymentStatus
from app.models.payment import Payment


class PaymentRepository:

    @staticmethod
    def create(db: Session, payment: Payment) -> Payment:
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return payment

    @staticmethod
    def get_by_id(db: Session, payment_id: uuid.UUID) -> Payment | None:
        return db.query(Payment).filter(Payment.id == payment_id).first()

    @staticmethod
    def get_by_order_id(db: Session, order_id: uuid.UUID) -> Payment | None:
        return db.query(Payment).filter(Payment.order_id == order_id).first()

    @staticmethod
    def get_by_razorpay_order_id(db: Session, razorpay_order_id: str) -> Payment | None:
        return db.query(Payment).filter(Payment.razorpay_order_id == razorpay_order_id).first()

    @staticmethod
    def update(db: Session, payment: Payment, update_data: dict[str, Any] | None = None) -> Payment:
        if update_data:
            for field, value in update_data.items():
                if hasattr(payment, field):
                    setattr(payment, field, value)

        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def mark_paid_if_pending(db: Session, payment_id: uuid.UUID) -> Payment | None:
        """Atomic PENDING -> PAID transition, e.g. for COD collection.

        Single UPDATE ... WHERE guards against two concurrent requests (an
        agent double-tapping "Collect") both succeeding: only the request
        that matches the WHERE clause at execution time affects a row, same
        pattern as OrderRepository.claim_pickup/claim_delivery.
        """
        affected = (
            db.query(Payment)
            .filter(Payment.id == payment_id, Payment.payment_status == PaymentStatus.PENDING)
            .update({Payment.payment_status: PaymentStatus.PAID}, synchronize_session=False)
        )
        db.commit()

        if affected != 1:
            return None

        return db.query(Payment).filter(Payment.id == payment_id).first()
