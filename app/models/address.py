import uuid
from decimal import Decimal

from sqlalchemy import String, Numeric, Boolean, ForeignKey

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.models.base import BaseModel


class Address(BaseModel):
    __tablename__ = "addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    label: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

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

    # an Address belongs to ONE User: address.user
    user = relationship(
        "User",
        back_populates="addresses"
    )
