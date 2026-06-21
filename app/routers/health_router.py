from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.health import StatusResponse


router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ApiResponse[StatusResponse])
def health():
    """Report whether the backend process is running."""
    return ApiResponse(
        success=True,
        message="Backend is healthy",
        data=StatusResponse(status="healthy"),
    )


@router.get(
    "/ready",
    response_model=ApiResponse[StatusResponse],
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ApiResponse[StatusResponse]}},
)
def ready(response: Response, db: Session = Depends(get_db)):
    """Report whether the database is accepting queries."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ApiResponse(
            success=False,
            message="Database is not ready",
            data=StatusResponse(status="not_ready"),
        )

    return ApiResponse(
        success=True,
        message="Database is ready",
        data=StatusResponse(status="ready"),
    )
