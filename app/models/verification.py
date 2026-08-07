from datetime import datetime
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import VerificationPurpose
from app.models.base import BaseModel


class Verification(BaseModel):

    __tablename__ = "verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    purpose: Mapped[VerificationPurpose] = mapped_column(
        Enum(VerificationPurpose),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="verifications",
    )