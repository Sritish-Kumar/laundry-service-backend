from decimal import Decimal

from sqlalchemy import String,Numeric,Boolean

from sqlalchemy.orm import Mapped,mapped_column

from app.models.base import BaseModel


class ServiceType(BaseModel):
    __tablename__ = "service_type"
    
    name: Mapped[str] = mapped_column(String,unique=True,nullable=False)
    
    description: Mapped[str] = mapped_column(String,nullable=True)
    
    current_price: Mapped[Decimal] = mapped_column(Numeric(10,2),nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean,default=True,nullable=False)
