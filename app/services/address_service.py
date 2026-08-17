import uuid
from sqlalchemy.orm import Session

from app.models import Address, User

from app.schemas.address import (
    AddressCreate,
    AddressUpdate,
    AddressResponse
)

from app.repo.address_repo import AddressRepository

from app.exceptions.custom_exceptions import (
    NotFoundError,
    ConflictError
)

MAX_ADDRESSES_PER_USER = 10


class AddressService:

    @staticmethod
    def create_address(db: Session, address_request: AddressCreate, user: User) -> AddressResponse:

        existing_count = AddressRepository.count_addresses_by_user(db, user.id)

        if existing_count >= MAX_ADDRESSES_PER_USER:
            raise ConflictError(f"You can have at most {MAX_ADDRESSES_PER_USER} addresses")

        if address_request.is_default:
            AddressRepository.clear_default_for_user(db, user.id)

        address = Address(
            user_id=user.id,
            **address_request.model_dump()
        )

        created_address = AddressRepository.create_address(db, address)

        return AddressResponse.model_validate(created_address)

    @staticmethod
    def list_addresses(db: Session, user: User) -> list[AddressResponse]:
        addresses = AddressRepository.get_addresses_by_user(db, user.id)

        return [AddressResponse.model_validate(address) for address in addresses]

    @staticmethod
    def update_address(
        db: Session,
        address_id: uuid.UUID,
        address_request: AddressUpdate,
        user: User
    ) -> AddressResponse:

        address = AddressRepository.get_address_by_id(db, address_id, user.id)

        if not address:
            raise NotFoundError("Address not found")

        update_data = address_request.model_dump(exclude_unset=True)

        if update_data.get("is_default") is True:
            AddressRepository.clear_default_for_user(db, user.id, exclude_address_id=address.id)

        updated_address = AddressRepository.update_address(db, address, update_data)

        return AddressResponse.model_validate(updated_address)

    @staticmethod
    def delete_address(db: Session, address_id: uuid.UUID, user: User) -> None:
        address = AddressRepository.get_address_by_id(db, address_id, user.id)

        if not address:
            raise NotFoundError("Address not found")

        AddressRepository.delete_address(db, address)
