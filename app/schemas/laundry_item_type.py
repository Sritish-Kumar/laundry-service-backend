import uuid

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)


class LaundryItemTypeCreateRequest(BaseModel):
    name: str = Field(min_length=2,max_length=100)

    description: str | None = Field(default=None,max_length=255)


class LaundryItemTypeUpdateRequest(BaseModel):
    name: str | None = Field(default=None,min_length=2,max_length=100)

    description: str | None = Field(default=None,max_length=255)

    is_active: bool | None = None


class LaundryItemTypeResponse(BaseModel):
    id: uuid.UUID

    name: str

    description: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
