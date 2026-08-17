from datetime import datetime

from sqlalchemy import String, Enum, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
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

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        nullable=False)

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True)

    # A User can have MANY Orders: user.orders
    # foreign_keys pins this to Order.user_id — orders also has
    # pickup_agent_id/delivery_agent_id FKs to users.id, which would
    # otherwise make the join ambiguous.
    orders = relationship(
        "Order",
        back_populates="user",
        foreign_keys="Order.user_id"
    )
    
    sessions = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all,delete-orphan"
    )

    verifications = relationship(
        "Verification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    addresses = relationship(
        "Address",
        back_populates="user",
        cascade="all, delete-orphan",
    )
