import uuid

from decimal import Decimal
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)


class ServicePricingCreateRequest(BaseModel):
    service_type_id: uuid.UUID

    laundry_item_type_id: uuid.UUID

    price: Decimal = Field(ge=0)


class ServicePricingUpdateRequest(BaseModel):
    price: Decimal | None = Field(default=None,ge=0)

    is_active: bool | None = None


class ServicePricingResponse(BaseModel):
    id: uuid.UUID

    service_type_id: uuid.UUID

    laundry_item_type_id: uuid.UUID

    price: Decimal

    is_active: bool

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class ServiceItemPriceResponse(BaseModel):
    item_type_id: uuid.UUID

    name: str

    price: Decimal
