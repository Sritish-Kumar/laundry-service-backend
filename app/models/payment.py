import uuid
from decimal import Decimal

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Enum
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.models.base import BaseModel
from app.core.constants import PaymentMethod, PaymentStatus


class Payment(BaseModel):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        unique=True
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod),
        nullable=False
    )

    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="INR"
    )

    # Present only for PaymentMethod.RAZORPAY; NULL for COD.
    razorpay_order_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    order = relationship(
        "Order",
        back_populates="payment"
    )
