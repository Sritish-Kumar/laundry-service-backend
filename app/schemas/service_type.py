import uuid

from decimal import Decimal
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict
)


class ServiceTypeCreateRequest(BaseModel):
    name: str

    description: str | None = None

    current_price: Decimal


class ServiceTypeResponse(BaseModel):
    id: uuid.UUID

    name: str

    description: str | None

    current_price: Decimal

    is_active: bool

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )