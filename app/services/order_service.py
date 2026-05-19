from decimal import Decimal
import random
import uuid
from sqlalchemy.orm import Session

from app.models import Order
from app.models.laundry_item import LaundryItem
from app.models.order_status_history import OrderStatusHistory

from app.schemas.order import (
    OrderCreateRequest,
    OrderResponse
)

from app.repo.order_repo import OrderRepository

from app.models.user import User


from app.exceptions.custom_exceptions import(
    NotFoundError,
    PermissionDeniedError,
    ConflictError
)

from app.core.workflow import VALID_ORDER_TRANSITIONS
from app.core.constants import UserRole,OrderStatus




class OrderService:
    
    @staticmethod
    def generate_order_number() -> str:
        random_number = random.randint(100000, 999999)
        return f"ORD-{random_number}"
    
    
    @staticmethod
    def create_order(db:Session, order_request: OrderCreateRequest, user: User) -> OrderResponse: 
        
        order = Order(
            public_order_number=OrderService.generate_order_number(),
            
            user_id=user.id,
            pickup_date=order_request.pickup_date,
            pickup_slot=order_request.pickup_slot,
        )
        
        total_price = Decimal(0)
        laundry_items = []
        
        for item_request in order_request.items:
            
            item_total = (item_request.quantity * item_request.service_price)
            
            laundry_item = LaundryItem(
                cloth_type=item_request.cloth_type,
                quantity=item_request.quantity,
                service_name_snapshot=item_request.service_name,
                service_price_snapshot=item_request.service_price,
                item_total_price=item_total
            )
            total_price += item_total
            laundry_items.append(laundry_item)
        
        order.total_price = float(total_price)
        order.items = laundry_items
        
        created_order =  OrderRepository.create_order(db, order)
        
        # as from_orm is deprecated, we can use model_validate with from_attributes=True in the schema config
        return OrderResponse.model_validate(created_order)


    @staticmethod
    def get_my_orders(db: Session, user: User) -> list[OrderResponse]:
        orders = OrderRepository.get_orders_by_user_id(db, user.id)
        
        if not orders:
            raise NotFoundError("No orders found for the user.")
        
        return [OrderResponse.model_validate(order) for order in orders]
    
    
    @staticmethod
    def get_order_by_id(db: Session, order_id: uuid.UUID, user: User) -> OrderResponse:
        order = OrderRepository.get_order_by_id(db, order_id)
        
        if not order:
            raise NotFoundError("Order not found.")
        
        if order.user_id != user.id:
            raise PermissionDeniedError("You do not have permission to access this order.")
        
        return OrderResponse.model_validate(order)
    
    @staticmethod
    def update_order_status(
        db:Session,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        user: User
    ) -> OrderResponse:
        if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
            raise PermissionDeniedError("Only Staff/Admin can update order status")
        
        
        order = OrderRepository.get_order_by_id(db,order_id)
        
        if not order:
            raise NotFoundError("Order Not Found")
        
        allowed_transitions = VALID_ORDER_TRANSITIONS[order.status]
        
        if new_status not in allowed_transitions:
            raise ConflictError(
                f"Invalid status transition "
                f"from {order.status} "
                f"to {new_status} "
            )
        
        ##
        order.status = new_status
        
        status_history = OrderStatusHistory(
            order_id = order_id,
            status = new_status,
            changed_by_user_id = user.id
            
        )
        
        
        ## Later belongs in the Repo layer but ok for now
        ## can be moved later ---------------------------
        db.add(status_history)
        db.commit()
        db.refresh(order)
        
        return OrderResponse.model_validate(order)
        
        