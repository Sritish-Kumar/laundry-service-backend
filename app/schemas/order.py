import uuid

from datetime import datetime,date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.core.constants import OrderStatus

# LaundryItem schemas

class LaundryItemCreate(BaseModel):
    
    cloth_type: str
    quantity: int
    service_name: str
    service_price: Decimal
    
    
class LaundryItemResponse(BaseModel):
    
    id: uuid.UUID
    cloth_type: str
    quantity: int
    service_name_snapshot: str
    service_price_snapshot: Decimal
    item_total_price: Decimal
    
    model_config = ConfigDict(from_attributes=True)
    

# Order schemas

class OrderCreateRequest(BaseModel):
    
    items: list[LaundryItemCreate]
    pickup_slot: str
    pickup_date: date
    
class OrderResponse(BaseModel):
    
    id: uuid.UUID
    public_order_number: str
    status: OrderStatus
    total_price: Decimal
    pickup_date: date
    pickup_slot: str
    created_at: datetime
    items: list[LaundryItemResponse]
    
    model_config = ConfigDict(from_attributes=True)
    
    
# status
class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus