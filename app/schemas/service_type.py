import uuid

from decimal import Decimal
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)


class ServiceTypeCreateRequest(BaseModel):
    name: str = Field(min_length=2,max_length=100)

    description: str | None = Field(default=None,max_length=255)

    current_price: Decimal = Field(gt=0)


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