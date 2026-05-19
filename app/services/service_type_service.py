from sqlalchemy.orm import Session

from app.models.service_type import (
    ServiceType
)

from app.schemas.service_type import (
    ServiceTypeCreateRequest
)

from app.repo.service_type_repo import (
    ServiceTypeRepository
)


class ServiceTypeService:

    @staticmethod
    def create_service_type(
        db: Session,
        payload: ServiceTypeCreateRequest
    ):
        service_type = ServiceType(
            name=payload.name,

            description=payload.description,

            current_price=payload.current_price
        )

        return (
            ServiceTypeRepository.create(
                db,
                service_type
            )
        )

    @staticmethod
    def get_all_service_types(
        db: Session
    ):
        return (
            ServiceTypeRepository.get_all(
                db
            )
        )