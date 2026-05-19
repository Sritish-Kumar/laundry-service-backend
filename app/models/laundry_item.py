import uuid

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
    
    # to be updated later to have different cloth type and different price for it
    cloth_type: Mapped[str] = mapped_column(
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
    
    service_price_snapshot: Mapped[float] = mapped_column(
        Numeric(10,2),
        nullable=False
    )
    
    item_total_price: Mapped[float] = mapped_column(
        Numeric(10,2),
        nullable=False
    )
    
    order = relationship(
        'Order',
        back_populates="items"
    )
    