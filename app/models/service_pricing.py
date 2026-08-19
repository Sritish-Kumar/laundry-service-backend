import uuid
from decimal import Decimal

from sqlalchemy import (
    Numeric,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint
)

from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.models.base import BaseModel


class ServicePricing(BaseModel):
    __tablename__ = "service_pricing"

    service_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_type.id"),
        nullable=False
    )

    laundry_item_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("laundry_item_type.id"),
        nullable=False
    )

    price: Mapped[Decimal] = mapped_column(Numeric(10,2),nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean,default=True,nullable=False)

    service_type = relationship(
        "ServiceType",
        back_populates="pricings"
    )

    laundry_item_type = relationship(
        "LaundryItemType",
        back_populates="pricings"
    )

    __table_args__ = (
        UniqueConstraint(
            "service_type_id",
            "laundry_item_type_id",
            name="uq_service_pricing_service_item"
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_service_pricing_price_non_negative"
        ),
    )
