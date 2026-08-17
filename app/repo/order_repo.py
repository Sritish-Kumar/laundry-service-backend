from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session,joinedload
import uuid

from app.models import Order
from app.core.constants import OrderStatus
from app.exceptions.custom_exceptions import ConflictError

class OrderRepository:

    @staticmethod
    def create_order(db:Session, order: Order) -> Order:
        # Order.items and Order.status_history are attached via SQLAlchemy
        # relationships before this call, so this single commit persists the
        # full Order + LaundryItems + OrderStatusHistory graph atomically.
        try:
            db.add(order)
            db.commit()
            db.refresh(order)
            return order
        except IntegrityError as exc:
            db.rollback()
            error_message = str(exc.orig).lower()

            if "public_order_number" in error_message:
                raise ConflictError("Order number collision") from exc

            raise


    @staticmethod
    def get_order_by_id(db: Session, order_id: uuid.UUID) -> Order | None:
        return db.query(Order).options(joinedload(Order.items)).filter(Order.id == order_id).first()
    
    #joinedload is used to eagerly load the related laundry items 
    # when fetching orders by user id, 
    # which helps to avoid the N+1 query problem and improves performance when accessing order details along with their items.

    @staticmethod
    def get_orders_by_user_id(
        db: Session, 
        user_id: uuid.UUID,
        status:OrderStatus|None,
        skip: int = 0,
        limit: int = 10 
        ) -> list[Order] | None:
        
        # return db.query(Order).options(joinedload(Order.items)).filter(Order.user_id == user_id).all()
        
        query = db.query(Order).options(joinedload(Order.items)).filter(Order.user_id==user_id)
        
        if status:
            query = query.filter(Order.status==status)
        
        return query.offset(skip).limit(limit).all()
    
    
    @staticmethod
    def get_order_by_status(
        db:Session,
        status
    ):
        """For Operational apis -> gets all order with the given status"""

        return db.query(Order).options(joinedload(Order.items)).filter(Order.status==status).all()

    ## Pagination to be implemeneted later

    @staticmethod
    def claim_pickup(db: Session, order_id: uuid.UUID, agent_id: uuid.UUID) -> bool:
        # Single atomic UPDATE ... WHERE guards against two agents claiming
        # the same order concurrently: only the request that matches the
        # WHERE clause at execution time affects a row.
        affected = (
            db.query(Order)
            .filter(
                Order.id == order_id,
                Order.status == OrderStatus.PENDING_PICKUP,
                Order.pickup_agent_id.is_(None),
            )
            .update({Order.pickup_agent_id: agent_id}, synchronize_session=False)
        )
        db.commit()
        return affected == 1

    @staticmethod
    def claim_delivery(db: Session, order_id: uuid.UUID, agent_id: uuid.UUID) -> bool:
        affected = (
            db.query(Order)
            .filter(
                Order.id == order_id,
                Order.status == OrderStatus.OUT_FOR_DELIVERY,
                Order.delivery_agent_id.is_(None),
            )
            .update({Order.delivery_agent_id: agent_id}, synchronize_session=False)
        )
        db.commit()
        return affected == 1

    @staticmethod
    def get_available_pickups(db: Session, skip: int = 0, limit: int = 10) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.status == OrderStatus.PENDING_PICKUP, Order.pickup_agent_id.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_my_pickups(db: Session, agent_id: uuid.UUID, skip: int = 0, limit: int = 10) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.pickup_agent_id == agent_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_available_deliveries(db: Session, skip: int = 0, limit: int = 10) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(
                Order.status == OrderStatus.OUT_FOR_DELIVERY,
                Order.delivery_agent_id.is_(None),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_my_deliveries(db: Session, agent_id: uuid.UUID, skip: int = 0, limit: int = 10) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.delivery_agent_id == agent_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
