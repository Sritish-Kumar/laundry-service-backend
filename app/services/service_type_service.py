import uuid

from sqlalchemy.orm import Session

from app.models.service_type import (
    ServiceType
)

from app.schemas.service_type import (
    ServiceTypeCreateRequest,
    ServiceTypeUpdateRequest
)

from app.repo.service_type_repo import (
    ServiceTypeRepository
)

from app.exceptions.custom_exceptions import (
    NotFoundError,
    ConflictError
)


class ServiceTypeService:

    @staticmethod
    def create_service_type(
        db: Session,
        payload: ServiceTypeCreateRequest
    ):
        if ServiceTypeRepository.get_by_name(db, payload.name):
            raise ConflictError("A service type with this name already exists")

        service_type = ServiceType(
            name=payload.name,

            description=payload.description
        )

        return (
            ServiceTypeRepository.create(
                db,
                service_type
            )
        )

    @staticmethod
    def get_all_service_types(
        db: Session,
        active_only: bool = True
    ):
        return (
            ServiceTypeRepository.get_all(
                db,
                active_only
            )
        )

    @staticmethod
    def get_service_type(
        db: Session,
        service_type_id: uuid.UUID
    ) -> ServiceType:
        service_type = ServiceTypeRepository.get_by_id(db, service_type_id)

        if not service_type:
            raise NotFoundError("Service type not found")

        return service_type

    @staticmethod
    def get_active_service_type(
        db: Session,
        service_type_id: uuid.UUID
    ) -> ServiceType:
        service_type = ServiceTypeService.get_service_type(db, service_type_id)

        if not service_type.is_active:
            raise NotFoundError("Service type not found")

        return service_type

    @staticmethod
    def update_service_type(
        db: Session,
        service_type_id: uuid.UUID,
        payload: ServiceTypeUpdateRequest
    ) -> ServiceType:
        service_type = ServiceTypeService.get_service_type(db, service_type_id)

        update_data = payload.model_dump(exclude_unset=True)

        new_name = update_data.get("name")
        if new_name and new_name != service_type.name:
            existing = ServiceTypeRepository.get_by_name(db, new_name)
            if existing and existing.id != service_type.id:
                raise ConflictError("A service type with this name already exists")

        return ServiceTypeRepository.update(db, service_type, update_data)
