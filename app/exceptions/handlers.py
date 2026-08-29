from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.custom_exceptions import (
    AuthenticationError,
    NotFoundError,
    ConflictError,
    PermissionDeniedError,
    ValidationError
    )

async def authentication_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "message": str(exc),
            "data": None,
        },
    )


async def not_found_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": str(exc),
            "data": None,
        },
    )


async def conflict_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "message": str(exc),
            "data": None,
        },
    )


async def permission_denied_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=403,
        content={
            "success": False,
            "message": str(exc),
            "data": None,
        },
    )


async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": str(exc),
            "data": None,
        },
    )