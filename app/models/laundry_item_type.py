from sqlalchemy import String,Boolean

from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.models.base import BaseModel


class LaundryItemType(BaseModel):
    __tablename__ = "laundry_item_type"

    name: Mapped[str] = mapped_column(String,unique=True,nullable=False)

    description: Mapped[str] = mapped_column(String,nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean,default=True,nullable=False)

    pricings = relationship(
        "ServicePricing",
        back_populates="laundry_item_type"
    )
