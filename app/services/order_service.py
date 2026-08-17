from datetime import date
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
from app.repo.service_type_repo import ServiceTypeRepository
from app.repo.address_repo import AddressRepository

from app.models.user import User


from app.exceptions.custom_exceptions import(
    NotFoundError,
    PermissionDeniedError,
    ConflictError
)

from app.core.workflow import VALID_ORDER_TRANSITIONS, TRANSITION_PERMISSIONS, AGENT_OWNERSHIP_TRANSITIONS
from app.core.constants import UserRole,OrderStatus

MAX_ORDER_NUMBER_ATTEMPTS = 5


class OrderService:

    @staticmethod
    def generate_order_number() -> str:
        date_part = date.today().strftime("%d%m%Y")
        random_part = f"{random.randint(0, 999999):06d}"
        return f"ORD-{date_part}-{random_part}"


    @staticmethod
    def create_order(db:Session, order_request: OrderCreateRequest, user: User) -> OrderResponse:

        address = AddressRepository.get_address_by_id(db, order_request.address_id, user.id)

        if not address:
            raise NotFoundError("Address not found")

        total_price = Decimal(0)
        item_snapshots = []

        for item_request in order_request.items:

            service_type = ServiceTypeRepository.get_by_id(db,item_request.service_type_id)

            if not service_type:
                raise NotFoundError("Service type Not Found")

            if not service_type.is_active:
                raise ConflictError("Service type is temp closed:< ")

            item_total = (item_request.quantity * service_type.current_price)

            total_price += item_total

            item_snapshots.append({
                "cloth_type": item_request.cloth_type,
                "quantity": item_request.quantity,
                "service_type_id": service_type.id,
                "service_name_snapshot": service_type.name,
                "service_price_snapshot": service_type.current_price,
                "item_total_price": item_total,
            })

        last_error: ConflictError | None = None

        for _ in range(MAX_ORDER_NUMBER_ATTEMPTS):

            order = Order(
                public_order_number=OrderService.generate_order_number(),

                user_id=user.id,
                status=OrderStatus.PENDING_PICKUP,
                total_price=total_price,
                pickup_date=order_request.pickup_date,
                pickup_slot=order_request.pickup_slot,

                recipient_name=address.recipient_name,
                recipient_phone=address.recipient_phone,
                address_line_1=address.address_line_1,
                address_line_2=address.address_line_2,
                landmark=address.landmark,
                city=address.city,
                state=address.state,
                postal_code=address.postal_code,
                country=address.country,
                latitude=address.latitude,
                longitude=address.longitude,
                location_accuracy=address.location_accuracy,
            )

            order.items = [LaundryItem(**snapshot) for snapshot in item_snapshots]

            order.status_history = [
                OrderStatusHistory(
                    status=OrderStatus.PENDING_PICKUP,
                    changed_by_user_id=user.id,
                )
            ]

            try:
                created_order = OrderRepository.create_order(db, order)
            except ConflictError as exc:
                last_error = exc
                continue

            # as from_orm is deprecated, we can use model_validate with from_attributes=True in the schema config
            return OrderResponse.model_validate(created_order)

        raise last_error or ConflictError("Could not generate a unique order number")


    @staticmethod
    def get_my_orders(db: Session, user: User, status:OrderStatus|None, skip: int = 0,limit: int = 10) -> list[OrderResponse]:
        
        orders = OrderRepository.get_orders_by_user_id(db, user.id,status,skip,limit)
        
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

        order = OrderRepository.get_order_by_id(db,order_id)

        if not order:
            raise NotFoundError("Order Not Found")

        # Step 1: is the transition itself valid, regardless of who's asking?
        allowed_transitions = VALID_ORDER_TRANSITIONS[order.status]

        if new_status not in allowed_transitions:
            raise ConflictError(
                f"Invalid status transition "
                f"from {order.status} "
                f"to {new_status} "
            )

        transition = (order.status, new_status)

        # Step 2: is this role allowed to perform this specific transition?
        allowed_roles = TRANSITION_PERMISSIONS.get(transition, [])

        if user.role not in allowed_roles:
            raise PermissionDeniedError(
                f"Role {user.role} is not permitted to move an order "
                f"from {order.status} to {new_status}"
            )

        # Step 3: ownership — a customer may only act on their own order, and
        # an agent must be the one actually assigned to it. ADMIN overrides
        # both (operational intervention); STAFF has no per-order ownership.
        if user.role == UserRole.CUSTOMER and order.user_id != user.id:
            raise PermissionDeniedError("You do not have permission to modify this order.")

        if user.role == UserRole.DELIVERY_AGENT:
            agent_field = AGENT_OWNERSHIP_TRANSITIONS.get(transition)

            if agent_field and getattr(order, agent_field) != user.id:
                raise PermissionDeniedError(
                    "You are not the delivery agent assigned to this order."
                )

        # Step 4 + 5: update status and create exactly one history record,
        # committed together atomically.
        order.status = new_status

        status_history = OrderStatusHistory(
            order_id=order_id,
            status=new_status,
            changed_by_user_id=user.id,
        )

        db.add(status_history)
        db.commit()
        db.refresh(order)

        return OrderResponse.model_validate(order)

    @staticmethod
    def claim_pickup(db: Session, order_id: uuid.UUID, user: User) -> OrderResponse:
        claimed = OrderRepository.claim_pickup(db, order_id, user.id)

        if not claimed:
            raise ConflictError("This order is no longer available for pickup claiming.")

        order = OrderRepository.get_order_by_id(db, order_id)
        return OrderResponse.model_validate(order)

    @staticmethod
    def claim_delivery(db: Session, order_id: uuid.UUID, user: User) -> OrderResponse:
        claimed = OrderRepository.claim_delivery(db, order_id, user.id)

        if not claimed:
            raise ConflictError("This order is no longer available for delivery claiming.")

        order = OrderRepository.get_order_by_id(db, order_id)
        return OrderResponse.model_validate(order)

    @staticmethod
    def get_available_pickups(db: Session, skip: int = 0, limit: int = 10) -> list[OrderResponse]:
        orders = OrderRepository.get_available_pickups(db, skip, limit)
        return [OrderResponse.model_validate(order) for order in orders]

    @staticmethod
    def get_my_pickups(db: Session, user: User, skip: int = 0, limit: int = 10) -> list[OrderResponse]:
        orders = OrderRepository.get_my_pickups(db, user.id, skip, limit)
        return [OrderResponse.model_validate(order) for order in orders]

    @staticmethod
    def get_available_deliveries(db: Session, skip: int = 0, limit: int = 10) -> list[OrderResponse]:
        orders = OrderRepository.get_available_deliveries(db, skip, limit)
        return [OrderResponse.model_validate(order) for order in orders]

    @staticmethod
    def get_my_deliveries(db: Session, user: User, skip: int = 0, limit: int = 10) -> list[OrderResponse]:
        orders = OrderRepository.get_my_deliveries(db, user.id, skip, limit)
        return [OrderResponse.model_validate(order) for order in orders]

    @staticmethod
    def get_operational_orders(
        db:Session,
        status:OrderStatus
    ):
        return OrderRepository.get_order_by_status(db,status)