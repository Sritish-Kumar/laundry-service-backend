import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.roles import require_roles
from app.models import User
from app.core.constants import UserRole

from app.schemas.order import OrderResponse
from app.schemas.common import ApiResponse

from app.services.order_service import OrderService


router = APIRouter(prefix="/delivery/orders", tags=["Delivery"])

# Claiming/viewing agent work pools is role-gated only (no per-order
# ownership to check yet — that's exactly what claiming establishes).
_agent_or_admin = require_roles([UserRole.DELIVERY_AGENT, UserRole.ADMIN])


@router.get("/pickups", response_model=List[OrderResponse])
def get_available_pickups(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(_agent_or_admin),
):
    """Orders awaiting pickup that no agent has claimed yet."""
    return OrderService.get_available_pickups(db, skip, limit)


@router.post("/{order_id}/pickup/claim", response_model=ApiResponse[OrderResponse])
def claim_pickup(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_agent_or_admin),
):
    """Atomically claim responsibility for picking up an order. Does not change order status."""
    order = OrderService.claim_pickup(db, order_id, current_user)

    return ApiResponse(
        success=True,
        message="Pickup claimed successfully",
        data=order,
    )


@router.get("/pickups/mine", response_model=List[OrderResponse])
def get_my_pickups(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(_agent_or_admin),
):
    return OrderService.get_my_pickups(db, current_user, skip, limit)


@router.get("/deliveries", response_model=List[OrderResponse])
def get_available_deliveries(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(_agent_or_admin),
):
    """Orders out for delivery that no agent has claimed yet."""
    return OrderService.get_available_deliveries(db, skip, limit)


@router.post("/{order_id}/delivery/claim", response_model=ApiResponse[OrderResponse])
def claim_delivery(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_agent_or_admin),
):
    """Atomically claim responsibility for delivering an order. Does not change order status."""
    order = OrderService.claim_delivery(db, order_id, current_user)

    return ApiResponse(
        success=True,
        message="Delivery claimed successfully",
        data=order,
    )


@router.get("/deliveries/mine", response_model=List[OrderResponse])
def get_my_deliveries(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(_agent_or_admin),
):
    return OrderService.get_my_deliveries(db, current_user, skip, limit)
