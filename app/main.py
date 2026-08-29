from fastapi import FastAPI
from app.routers.auth_router import router as auth_router
from app.routers.user_router import router as user_router
from app.routers.address_router import router as address_router
from app.routers.order_router import router as order_router
from app.routers.delivery_router import router as delivery_router
from app.routers.operations_router import router as operations_router
from app.routers.service_type_router import router as service_type_router
from app.routers.laundry_item_type_router import router as laundry_item_type_router
from app.routers.service_pricing_router import router as service_pricing_router
from app.routers.health_router import router as health_router
from app.routers.payment_router import router as payment_router

from app.exceptions.custom_exceptions import (
    AuthenticationError,
    NotFoundError,
    ConflictError,
    PermissionDeniedError,
    ValidationError
    )
from app.exceptions.handlers import (
    authentication_exception_handler,
    not_found_exception_handler,
    conflict_exception_handler,
    permission_denied_exception_handler,
    validation_exception_handler
    )

from app.middlewares.logging import RequestLoggingMiddleware

app = FastAPI(
    title="Laundry Service API",
    version="1.0.0",
    description="API for managing laundry services"
)

app.add_exception_handler(AuthenticationError, authentication_exception_handler)  
app.add_exception_handler(NotFoundError, not_found_exception_handler)  
app.add_exception_handler(ConflictError, conflict_exception_handler)  
app.add_exception_handler(PermissionDeniedError, permission_denied_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(address_router)
app.include_router(order_router)
app.include_router(delivery_router)
app.include_router(operations_router)
app.include_router(service_type_router)
app.include_router(laundry_item_type_router)
app.include_router(service_pricing_router)
app.include_router(health_router)
app.include_router(payment_router)

app.add_middleware(RequestLoggingMiddleware)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Laundry Service API!"}
