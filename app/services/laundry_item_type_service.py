import uuid

from sqlalchemy.orm import Session

from app.models.laundry_item_type import LaundryItemType

from app.schemas.laundry_item_type import (
    LaundryItemTypeCreateRequest,
    LaundryItemTypeUpdateRequest
)

from app.repo.laundry_item_type_repo import (
    LaundryItemTypeRepository
)

from app.exceptions.custom_exceptions import (
    NotFoundError,
    ConflictError
)


class LaundryItemTypeService:

    @staticmethod
    def create_laundry_item_type(
        db: Session,
        payload: LaundryItemTypeCreateRequest
    ) -> LaundryItemType:
        if LaundryItemTypeRepository.get_by_name(db, payload.name):
            raise ConflictError("A laundry item type with this name already exists")

        laundry_item_type = LaundryItemType(
            name=payload.name,

            description=payload.description
        )

        return LaundryItemTypeRepository.create(db, laundry_item_type)

    @staticmethod
    def get_all_laundry_item_types(db: Session, active_only: bool = True):
        return LaundryItemTypeRepository.get_all(db, active_only)

    @staticmethod
    def get_laundry_item_type(
        db: Session,
        laundry_item_type_id: uuid.UUID
    ) -> LaundryItemType:
        laundry_item_type = LaundryItemTypeRepository.get_by_id(db, laundry_item_type_id)

        if not laundry_item_type:
            raise NotFoundError("Laundry item type not found")

        return laundry_item_type

    @staticmethod
    def get_active_laundry_item_type(
        db: Session,
        laundry_item_type_id: uuid.UUID
    ) -> LaundryItemType:
        laundry_item_type = LaundryItemTypeService.get_laundry_item_type(db, laundry_item_type_id)

        if not laundry_item_type.is_active:
            raise NotFoundError("Laundry item type not found")

        return laundry_item_type

    @staticmethod
    def update_laundry_item_type(
        db: Session,
        laundry_item_type_id: uuid.UUID,
        payload: LaundryItemTypeUpdateRequest
    ) -> LaundryItemType:
        laundry_item_type = LaundryItemTypeService.get_laundry_item_type(db, laundry_item_type_id)

        update_data = payload.model_dump(exclude_unset=True)

        new_name = update_data.get("name")
        if new_name and new_name != laundry_item_type.name:
            existing = LaundryItemTypeRepository.get_by_name(db, new_name)
            if existing and existing.id != laundry_item_type.id:
                raise ConflictError("A laundry item type with this name already exists")

        return LaundryItemTypeRepository.update(db, laundry_item_type, update_data)
