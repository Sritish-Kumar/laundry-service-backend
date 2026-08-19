import uuid
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.service_pricing import ServicePricing


class ServicePricingRepository:

    @staticmethod
    def create(db: Session, service_pricing: ServicePricing) -> ServicePricing:
        db.add(service_pricing)
        db.commit()
        db.refresh(service_pricing)
        return service_pricing

    @staticmethod
    def get_by_id(db: Session, service_pricing_id) -> ServicePricing | None:
        return db.query(ServicePricing).filter(ServicePricing.id == service_pricing_id).first()

    @staticmethod
    def get_by_service_type(db: Session, service_type_id: uuid.UUID) -> list[ServicePricing]:
        return (
            db.query(ServicePricing)
            .options(joinedload(ServicePricing.laundry_item_type))
            .filter(ServicePricing.service_type_id == service_type_id)
            .all()
        )

    @staticmethod
    def get_pricing(
        db: Session,
        service_type_id: uuid.UUID,
        laundry_item_type_id: uuid.UUID,
        active_only: bool = False,
    ) -> ServicePricing | None:
        query = db.query(ServicePricing).filter(
            ServicePricing.service_type_id == service_type_id,
            ServicePricing.laundry_item_type_id == laundry_item_type_id,
        )

        if active_only:
            query = query.filter(ServicePricing.is_active.is_(True))

        return query.first()

    @staticmethod
    def update(db: Session, service_pricing: ServicePricing, update_data: dict[str, Any] | None = None) -> ServicePricing:
        if update_data:
            for field, value in update_data.items():
                if hasattr(service_pricing, field):
                    setattr(service_pricing, field, value)

        db.add(service_pricing)
        db.commit()
        db.refresh(service_pricing)
        return service_pricing
