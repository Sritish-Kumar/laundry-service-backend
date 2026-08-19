import uuid
from decimal import Decimal

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from sqlalchemy import (
    String,
    ForeignKey,
    Numeric,
    Integer
)


from app.models.base import BaseModel


class LaundryItem(BaseModel):
    __tablename__ = "laundry_items"
    
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False
    )
    
    laundry_item_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("laundry_item_type.id"),
        nullable=False
    )

    item_type_name_snapshot: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    service_name_snapshot: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    
    service_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(10,2),
        nullable=False
    )
    
    item_total_price: Mapped[Decimal] = mapped_column(
        Numeric(10,2),
        nullable=False
    )
    
    service_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_type.id"),
        nullable=False
    )
    
    service_type = relationship(
        "ServiceType"
    )
    laundry_item_type = relationship(
        "LaundryItemType"
    )
    order = relationship(
        'Order',
        back_populates="items"
    )
    
