from sqlalchemy.orm import Session
from typing import Any
import uuid

from app.models import Address


class AddressRepository:

    @staticmethod
    def create_address(db: Session, address: Address) -> Address:
        db.add(address)
        db.commit()
        db.refresh(address)
        return address

    @staticmethod
    def get_address_by_id(db: Session, address_id: uuid.UUID, user_id: uuid.UUID) -> Address | None:
        return (
            db.query(Address)
            .filter(Address.id == address_id, Address.user_id == user_id)
            .first()
        )

    @staticmethod
    def get_addresses_by_user(db: Session, user_id: uuid.UUID) -> list[Address]:
        return db.query(Address).filter(Address.user_id == user_id).all()

    @staticmethod
    def count_addresses_by_user(db: Session, user_id: uuid.UUID) -> int:
        return db.query(Address).filter(Address.user_id == user_id).count()

    @staticmethod
    def clear_default_for_user(db: Session, user_id: uuid.UUID, exclude_address_id: uuid.UUID | None = None) -> None:
        query = db.query(Address).filter(Address.user_id == user_id, Address.is_default.is_(True))

        if exclude_address_id is not None:
            query = query.filter(Address.id != exclude_address_id)

        query.update({Address.is_default: False}, synchronize_session=False)

    @staticmethod
    def update_address(db: Session, address: Address, update_data: dict[str, Any] | None = None) -> Address:
        if update_data:
            for field, value in update_data.items():
                if hasattr(address, field):
                    setattr(address, field, value)

        db.add(address)
        db.commit()
        db.refresh(address)
        return address

    @staticmethod
    def delete_address(db: Session, address: Address) -> None:
        db.delete(address)
        db.commit()
