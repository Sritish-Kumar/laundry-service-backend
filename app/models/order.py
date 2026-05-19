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

    # an Order belongs to ONE User: order.user
    user = relationship(
        "User",
        back_populates="orders"
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
    
    
