import uuid

from datetime import datetime,date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict,Field

from app.core.constants import OrderStatus, PaymentMethod
from app.schemas.payment import PaymentResponse

# LaundryItem schemas

class LaundryItemCreate(BaseModel):

    laundry_item_type_id: uuid.UUID
    quantity: int = Field(gt=0,le=100)
    service_type_id : uuid.UUID

class LaundryItemResponse(BaseModel):

    id: uuid.UUID
    item_type_name_snapshot: str
    quantity: int
    service_name_snapshot: str
    service_price_snapshot: Decimal
    item_total_price: Decimal

    model_config = ConfigDict(from_attributes=True)
    

# Order schemas

class OrderCreateRequest(BaseModel):

    address_id: uuid.UUID
    items: list[LaundryItemCreate]
    pickup_slot: str
    pickup_date: date
    # The frontend only chooses how it intends to pay — amount, status, and
    # any provider IDs are always backend-controlled. Defaults to RAZORPAY
    # so existing clients that predate COD keep working unchanged.
    payment_method: PaymentMethod = PaymentMethod.RAZORPAY

class OrderResponse(BaseModel):

    id: uuid.UUID
    public_order_number: str
    status: OrderStatus
    total_price: Decimal
    pickup_date: date
    pickup_slot: str
    created_at: datetime
    items: list[LaundryItemResponse]

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

    # Payment is created alongside the Order, so this should never actually
    # be None in practice — Optional here only guards against a stale row
    # from before Payment existed.
    payment: PaymentResponse | None = None

    model_config = ConfigDict(from_attributes=True)


# status
class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus