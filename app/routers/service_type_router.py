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

from app.schemas.service_type import (
    ServiceTypeCreateRequest,
    ServiceTypeUpdateRequest,
    ServiceTypeResponse
)

from app.schemas.service_pricing import (
    ServiceItemPriceResponse
)

from app.services.service_type_service import (
    ServiceTypeService
)

from app.services.service_pricing_service import (
    ServicePricingService
)


router = APIRouter(
    prefix="/service-types",
    tags=["Service Types"]
)

_admin_only = require_roles([UserRole.ADMIN])


@router.post(
    "",
    response_model=ServiceTypeResponse
)
def create_service_type(
    payload: ServiceTypeCreateRequest,

    db: Session = Depends(get_db),

    current_user=Depends(_admin_only)
):
    return (
        ServiceTypeService.create_service_type(
            db,
            payload
        )
    )


@router.get(
    "",
    response_model=List[ServiceTypeResponse]
)
def get_all_service_types(
    db: Session = Depends(get_db)
):
    return (
        ServiceTypeService.get_all_service_types(
            db
        )
    )


@router.get(
    "/{service_type_id}",
    response_model=ServiceTypeResponse
)
def get_service_type(
    service_type_id: uuid.UUID,

    db: Session = Depends(get_db)
):
    return (
        ServiceTypeService.get_active_service_type(
            db,
            service_type_id
        )
    )


@router.patch(
    "/{service_type_id}",
    response_model=ServiceTypeResponse
)
def update_service_type(
    service_type_id: uuid.UUID,
    payload: ServiceTypeUpdateRequest,

    db: Session = Depends(get_db),

    current_user=Depends(_admin_only)
):
    return (
        ServiceTypeService.update_service_type(
            db,
            service_type_id,
            payload
        )
    )


@router.get(
    "/{service_type_id}/items",
    response_model=List[ServiceItemPriceResponse]
)
def get_items_for_service(
    service_type_id: uuid.UUID,

    db: Session = Depends(get_db)
):
    return (
        ServicePricingService.get_items_for_service(
            db,
            service_type_id
        )
    )