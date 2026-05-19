from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.custom_exceptions import (
    AuthenticationError,
    NotFoundError,
    ConflictError,
    PermissionDeniedError
    )

async def authentication_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)}
    )

async def not_found_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )

async def conflict_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc)}
    )

async def permission_denied_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc)}
    )