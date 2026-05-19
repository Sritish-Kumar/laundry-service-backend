import uuid

from sqlalchemy import ForeignKey,Enum

from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.models.base import BaseModel
from app.core.constants import OrderStatus


class OrderStatusHistory(BaseModel):
    
    __tablename__ = "order_status_history"
    
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    order = relationship("Order", back_populates="status_history")