import uuid

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

from app.schemas.service_pricing import (
    ServicePricingCreateRequest,
    ServicePricingUpdateRequest,
    ServicePricingResponse
)

from app.services.service_pricing_service import (
    ServicePricingService
)


router = APIRouter(
    prefix="/service-pricing",
    tags=["Service Pricing"]
)

_admin_only = require_roles([UserRole.ADMIN])


@router.post(
    "",
    response_model=ServicePricingResponse
)
def create_service_pricing(
    payload: ServicePricingCreateRequest,

    db: Session = Depends(get_db),

    current_user=Depends(_admin_only)
):
    return (
        ServicePricingService.create_service_pricing(
            db,
            payload
        )
    )


@router.get(
    "/{service_pricing_id}",
    response_model=ServicePricingResponse
)
def get_service_pricing(
    service_pricing_id: uuid.UUID,

    db: Session = Depends(get_db),

    current_user=Depends(_admin_only)
):
    return (
        ServicePricingService.get_pricing_by_id(
            db,
            service_pricing_id
        )
    )


@router.patch(
    "/{service_pricing_id}",
    response_model=ServicePricingResponse
)
def update_service_pricing(
    service_pricing_id: uuid.UUID,
    payload: ServicePricingUpdateRequest,

    db: Session = Depends(get_db),

    current_user=Depends(_admin_only)
):
    return (
        ServicePricingService.update_service_pricing(
            db,
            service_pricing_id,
            payload
        )
    )
