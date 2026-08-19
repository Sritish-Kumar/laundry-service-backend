from typing import Any

from sqlalchemy.orm import Session

from app.models.laundry_item_type import LaundryItemType


class LaundryItemTypeRepository:

    @staticmethod
    def create(db: Session, laundry_item_type: LaundryItemType) -> LaundryItemType:
        db.add(laundry_item_type)
        db.commit()
        db.refresh(laundry_item_type)
        return laundry_item_type

    @staticmethod
    def get_all(db: Session, active_only: bool = False):
        query = db.query(LaundryItemType)

        if active_only:
            query = query.filter(LaundryItemType.is_active.is_(True))

        return query.all()

    @staticmethod
    def get_by_id(db: Session, laundry_item_type_id) -> LaundryItemType | None:
        return db.query(LaundryItemType).filter(LaundryItemType.id == laundry_item_type_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> LaundryItemType | None:
        return db.query(LaundryItemType).filter(LaundryItemType.name == name).first()

    @staticmethod
    def update(db: Session, laundry_item_type: LaundryItemType, update_data: dict[str, Any] | None = None) -> LaundryItemType:
        if update_data:
            for field, value in update_data.items():
                if hasattr(laundry_item_type, field):
                    setattr(laundry_item_type, field, value)

        db.add(laundry_item_type)
        db.commit()
        db.refresh(laundry_item_type)
        return laundry_item_type
