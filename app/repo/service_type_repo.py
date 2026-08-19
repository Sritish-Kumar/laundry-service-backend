from typing import Any

from sqlalchemy.orm import Session
from app.models.service_type import ServiceType

class ServiceTypeRepository:

    @staticmethod
    def create(db: Session,
               service_type: ServiceType) -> ServiceType:

        db.add(service_type)
        db.commit()
        db.refresh(service_type)

        return service_type


    @staticmethod
    def get_all(db:Session, active_only: bool = False):
        query = db.query(ServiceType)

        if active_only:
            query = query.filter(ServiceType.is_active.is_(True))

        return query.all()

    @staticmethod
    def get_by_id(db: Session,service_type_id):
        return db.query(ServiceType).filter(ServiceType.id==service_type_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> ServiceType | None:
        return db.query(ServiceType).filter(ServiceType.name == name).first()

    @staticmethod
    def update(db: Session, service_type: ServiceType, update_data: dict[str, Any] | None = None) -> ServiceType:
        if update_data:
            for field, value in update_data.items():
                if hasattr(service_type, field):
                    setattr(service_type, field, value)

        db.add(service_type)
        db.commit()
        db.refresh(service_type)
        return service_type
