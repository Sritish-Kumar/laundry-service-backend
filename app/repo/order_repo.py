from sqlalchemy.orm import Session,joinedload
import uuid

from app.models import Order
from app.core.constants import OrderStatus

class OrderRepository:
    
    @staticmethod
    def create_order(db:Session, order: Order) -> Order:
        
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    

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
    