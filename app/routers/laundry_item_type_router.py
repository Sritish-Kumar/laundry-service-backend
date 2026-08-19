import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.dependencies.database import (
    get_db
)

from app.dependencies.roles import (
    require_roles
)

from app.core.constants import (
    UserRole
)

from app.schemas.laundry_item_type import (
    LaundryItemTypeCreateRequest,
    LaundryItemTypeUpdateRequest,
    LaundryItemTypeResponse
)

from app.services.laundry_item_type_service import (
    LaundryItemTypeService
)


router = APIRouter(
    prefix="/item-types",
    tags=["Laundry Item Types"]
)

_admin_only = require_roles([UserRole.ADMIN])


@router.post(
    "",
    response_model=LaundryItemTypeResponse
)
def create_laundry_item_type(
    payload: LaundryItemTypeCreateRequest,

    db: Session = Depends(get_db),

    current_user=Depends(_admin_only)
):
    return (
        LaundryItemTypeService.create_laundry_item_type(
            db,
            payload
        )
    )


@router.get(
    "",
    response_model=List[LaundryItemTypeResponse]
)
def get_all_laundry_item_types(
    db: Session = Depends(get_db)
):
    return (
        LaundryItemTypeService.get_all_laundry_item_types(
            db
        )
    )


@router.get(
    "/{laundry_item_type_id}",
    response_model=LaundryItemTypeResponse
)
def get_laundry_item_type(
    laundry_item_type_id: uuid.UUID,

    db: Session = Depends(get_db)
):
    return (
        LaundryItemTypeService.get_active_laundry_item_type(
            db,
            laundry_item_type_id
        )
    )


@router.patch(
    "/{laundry_item_type_id}",
    response_model=LaundryItemTypeResponse
)
def update_laundry_item_type(
    laundry_item_type_id: uuid.UUID,
    payload: LaundryItemTypeUpdateRequest,

    db: Session = Depends(get_db),

    current_user=Depends(_admin_only)
):
    return (
        LaundryItemTypeService.update_laundry_item_type(
            db,
            laundry_item_type_id,
            payload
        )
    )
