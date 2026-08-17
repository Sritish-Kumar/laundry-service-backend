import uuid
from decimal import Decimal

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Enum,
    Date
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.models.base import BaseModel
from app.core.constants import OrderStatus


class Order(BaseModel):
    __tablename__ = "orders"
    
    public_order_number: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING_PICKUP
    )

    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0
    )

    pickup_date: Mapped[Date] = mapped_column(
        Date,
        nullable=False
    )

    pickup_slot: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    # Address snapshot — copied from the selected Address at order-creation
    # time. Intentionally not a FK; the Order must not change if the saved
    # Address is later edited or deleted.
    recipient_name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    recipient_phone: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    address_line_1: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    address_line_2: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    landmark: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    city: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    state: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    postal_code: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    country: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    latitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False
    )

    longitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False
    )

    location_accuracy: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True
    )

    # Self-claimed by a DELIVERY_AGENT; nullable until claimed. Not a
    # dedicated OrderAssignment table by design — see Phase 11.5.
    pickup_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    delivery_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    # an Order belongs to ONE User: order.user
    # foreign_keys is required now that orders has three FKs to users.id
    # (user_id, pickup_agent_id, delivery_agent_id) — otherwise SQLAlchemy
    # can't infer which column this relationship should join on.
    user = relationship(
        "User",
        back_populates="orders",
        foreign_keys=[user_id]
    )

    items = relationship(
        "LaundryItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    
    
