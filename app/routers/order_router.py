from fastapi import APIRouter, Depends
from typing import List,Optional
import uuid
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models import User
from app.schemas.order import OrderCreateRequest, OrderResponse,UpdateOrderStatusRequest
from app.schemas.common import ApiResponse

from app.services.order_service import OrderService
from app.core.constants import OrderStatus

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse)
def create_order(
    order_data: OrderCreateRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
    ):
    
    """Create a new order for the authenticated user"""
    order =  OrderService.create_order(db, order_data, current_user)
    
    ## Standardized response object can be implemted on other routes too later
    return ApiResponse(
        success=True,
        message="Order Created Successfully",
        data=OrderResponse.model_validate(order)
    )
    

@router.get("/", response_model=List[OrderResponse])
def get_my_orders(
    status: Optional[OrderStatus] = None,
    skip: int = 0,
    limit: int = 10,
    
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
    ):
    
    """Get all orders for the authenticated user"""
    return OrderService.get_my_orders(db, current_user,status,skip,limit)

@router.get("/{order_id}", response_model=OrderResponse)
def get_order_by_id(
    order_id: uuid.UUID, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
    ):
    
    """Get a specific order by ID for the authenticated user"""
    return OrderService.get_order_by_id(db, order_id, current_user)


@router.patch("/{order_id}/status",response_model=OrderResponse)
def update_order_status(
    order_id: uuid.UUID,
    order_data: UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    
    return OrderService.update_order_status(db,order_id,order_data.status,current_user)