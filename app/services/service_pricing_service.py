import uuid

from sqlalchemy.orm import Session

from app.models.service_pricing import ServicePricing

from app.schemas.service_pricing import (
    ServicePricingCreateRequest,
    ServicePricingUpdateRequest,
    ServiceItemPriceResponse
)

from app.repo.service_pricing_repo import (
    ServicePricingRepository
)

from app.services.service_type_service import ServiceTypeService
from app.services.laundry_item_type_service import LaundryItemTypeService

from app.exceptions.custom_exceptions import (
    NotFoundError,
    ConflictError
)


class ServicePricingService:

    @staticmethod
    def create_service_pricing(
        db: Session,
        payload: ServicePricingCreateRequest
    ) -> ServicePricing:
        service_type = ServiceTypeService.get_service_type(db, payload.service_type_id)
        laundry_item_type = LaundryItemTypeService.get_laundry_item_type(db, payload.laundry_item_type_id)

        if not service_type.is_active or not laundry_item_type.is_active:
            raise ConflictError(
                "Cannot create active pricing for an inactive service type or laundry item type"
            )

        if ServicePricingRepository.get_pricing(db, service_type.id, laundry_item_type.id):
            raise ConflictError(
                "Pricing already exists for this service type and laundry item type combination"
            )

        service_pricing = ServicePricing(
            service_type_id=service_type.id,
            laundry_item_type_id=laundry_item_type.id,
            price=payload.price
        )

        return ServicePricingRepository.create(db, service_pricing)

    @staticmethod
    def get_pricing_by_id(
        db: Session,
        service_pricing_id: uuid.UUID
    ) -> ServicePricing:
        service_pricing = ServicePricingRepository.get_by_id(db, service_pricing_id)

        if not service_pricing:
            raise NotFoundError("Service pricing not found")

        return service_pricing

    @staticmethod
    def get_items_for_service(
        db: Session,
        service_type_id: uuid.UUID,
        active_only: bool = True
    ) -> list[ServiceItemPriceResponse]:
        service_type = ServiceTypeService.get_service_type(db, service_type_id)

        pricings = ServicePricingRepository.get_by_service_type(db, service_type_id)

        if active_only:
            pricings = [
                pricing
                for pricing in pricings
                if service_type.is_active
                and pricing.is_active
                and pricing.laundry_item_type.is_active
            ]

        return [
            ServiceItemPriceResponse(
                item_type_id=pricing.laundry_item_type_id,
                name=pricing.laundry_item_type.name,
                price=pricing.price
            )
            for pricing in pricings
        ]

    @staticmethod
    def update_service_pricing(
        db: Session,
        service_pricing_id: uuid.UUID,
        payload: ServicePricingUpdateRequest
    ) -> ServicePricing:
        service_pricing = ServicePricingService.get_pricing_by_id(db, service_pricing_id)

        update_data = payload.model_dump(exclude_unset=True)

        if update_data.get("is_active") is True:
            service_type = ServiceTypeService.get_service_type(db, service_pricing.service_type_id)
            laundry_item_type = LaundryItemTypeService.get_laundry_item_type(
                db, service_pricing.laundry_item_type_id
            )

            if not service_type.is_active or not laundry_item_type.is_active:
                raise ConflictError(
                    "Cannot activate pricing for an inactive service type or laundry item type"
                )

        return ServicePricingRepository.update(db, service_pricing, update_data)
