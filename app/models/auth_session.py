from typing import Optional
from datetime import datetime
from sqlalchemy import String, Enum,Boolean,ForeignKey,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.models.base import BaseModel
from app.core.constants import UserRole
import uuid
from app.core.constants import DeviceType

class AuthSession(BaseModel):
    
    __tablename__ = "auth_sessions"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    ) 
    
    refresh_token_hash : Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        unique=True
    )
    
    device_name : Mapped[str| None] = mapped_column(
        String(255),
    )
    
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType),
        nullable=False
    )
    
    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        
    )
    
    ip_address: Mapped[str | None] = mapped_column(
        String(45)
    )

    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    user = relationship(
        "User", 
        back_populates="sessions"
    )