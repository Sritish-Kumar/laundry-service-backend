from typing import List

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.roles import require_roles
from app.core.constants import UserRole,OrderStatus

from  app.schemas.order import OrderResponse
from app.services.order_service import OrderService


router = APIRouter(prefix="/operations",
                   tags=["Operations"])


@router.get("/orders",
            response_model=List[OrderResponse])
def get_operational_orders(
    status: OrderStatus,
    db: Session = Depends(get_db),
    
    current_user = Depends(
        require_roles([
            UserRole.STAFF,
            UserRole.ADMIN
        ])
    )
):
    return OrderService.get_operational_orders(db,status)
    