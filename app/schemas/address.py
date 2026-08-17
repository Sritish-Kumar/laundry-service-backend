import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AddressCreate(BaseModel):

    label: str
    is_default: bool = False

    recipient_name: str
    recipient_phone: str

    address_line_1: str
    address_line_2: str | None = None
    landmark: str | None = None

    city: str
    state: str
    postal_code: str
    country: str

    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    location_accuracy: Decimal | None = Field(default=None, ge=0)


class AddressUpdate(BaseModel):

    label: str | None = None
    is_default: bool | None = None

    recipient_name: str | None = None
    recipient_phone: str | None = None

    address_line_1: str | None = None
    address_line_2: str | None = None
    landmark: str | None = None

    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    location_accuracy: Decimal | None = Field(default=None, ge=0)


class AddressResponse(BaseModel):

    id: uuid.UUID
    label: str
    is_default: bool

    recipient_name: str
    recipient_phone: str

    address_line_1: str
    address_line_2: str | None
    landmark: str | None

    city: str
    state: str
    postal_code: str
    country: str

    latitude: Decimal
    longitude: Decimal
    location_accuracy: Decimal | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
