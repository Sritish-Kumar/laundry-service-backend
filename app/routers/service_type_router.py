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
    ServiceTypeResponse
)

from app.services.service_type_service import (
    ServiceTypeService
)


router = APIRouter(
    prefix="/service-types",
    tags=["Service Types"]
)


@router.post(
    "",
    response_model=ServiceTypeResponse
)
def create_service_type(
    payload: ServiceTypeCreateRequest,

    db: Session = Depends(get_db),

    current_user=Depends(
        require_roles([
            UserRole.ADMIN
        ])
    )
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