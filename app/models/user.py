from sqlalchemy import String, Enum,Boolean
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.models.base import BaseModel
from app.core.constants import UserRole

class User(BaseModel):
    __tablename__ = "users"
    
    full_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False)
    
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False)
    
    phone: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False)
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False)
    
    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        default=True,
        nullable=False)
    
    # A User can have MANY Orders: user.orders
    orders = relationship(
        "Order",
        back_populates="user"
    )