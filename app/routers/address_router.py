import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models import User

from app.schemas.address import (
    AddressCreate,
    AddressUpdate,
    AddressResponse
)
from app.schemas.common import ApiResponse

from app.services.address_service import AddressService


router = APIRouter(prefix="/users/me/addresses", tags=["Addresses"])


@router.get("", response_model=ApiResponse[list[AddressResponse]])
def list_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    addresses = AddressService.list_addresses(db, current_user)

    return ApiResponse(
        success=True,
        message="Addresses retrieved successfully",
        data=addresses
    )


@router.post("", response_model=ApiResponse[AddressResponse], status_code=201)
def create_address(
    address_data: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    address = AddressService.create_address(db, address_data, current_user)

    return ApiResponse(
        success=True,
        message="Address created successfully",
        data=address
    )


@router.patch("/{address_id}", response_model=ApiResponse[AddressResponse])
def update_address(
    address_id: uuid.UUID,
    address_data: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    address = AddressService.update_address(db, address_id, address_data, current_user)

    return ApiResponse(
        success=True,
        message="Address updated successfully",
        data=address
    )


@router.delete("/{address_id}", response_model=ApiResponse[None])
def delete_address(
    address_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    AddressService.delete_address(db, address_id, current_user)

    return ApiResponse(
        success=True,
        message="Address deleted successfully",
        data=None
    )
