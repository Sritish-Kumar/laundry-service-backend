from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Any
import uuid

from app.exceptions.custom_exceptions import ConflictError
from app.models import User


class UserRepository:

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_phone(db: Session, phone: str) -> User | None:
        return db.query(User).filter(User.phone == phone).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(db: Session, user: User) -> User:
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError as exc:
            db.rollback()
            error_message = str(exc.orig).lower()

            if "phone" in error_message:
                raise ConflictError("A user with this phone number already exists") from exc
            if "email" in error_message:
                raise ConflictError("A user with this email already exists") from exc

            raise ConflictError("User registration failed due to a data conflict") from exc

    @staticmethod
    def update_user(
        db: Session,
        user: User,
        update_data: dict[str, Any] | None = None,
    ) -> User:
        if update_data:
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user
