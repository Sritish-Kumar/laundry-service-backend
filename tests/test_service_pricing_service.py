import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.exceptions.custom_exceptions import ConflictError, NotFoundError
from app.schemas.laundry_item_type import LaundryItemTypeCreateRequest, LaundryItemTypeUpdateRequest
from app.schemas.service_pricing import ServicePricingCreateRequest, ServicePricingUpdateRequest
from app.schemas.service_type import ServiceTypeCreateRequest, ServiceTypeUpdateRequest
from app.services.laundry_item_type_service import LaundryItemTypeService
from app.services.service_pricing_service import ServicePricingService
from app.services.service_type_service import ServiceTypeService


def _make_service_type(db_session, name=None):
    payload = ServiceTypeCreateRequest(
        name=name or f"Wash {uuid.uuid4().hex[:8]}",
        description="A wash service",
    )
    return ServiceTypeService.create_service_type(db_session, payload)


def _make_item_type(db_session, name=None):
    payload = LaundryItemTypeCreateRequest(
        name=name or f"Shirt {uuid.uuid4().hex[:8]}",
        description="A shirt",
    )
    return LaundryItemTypeService.create_laundry_item_type(db_session, payload)


def test_create_service_pricing(db_session):
    service_type = _make_service_type(db_session)
    item_type = _make_item_type(db_session)

    pricing = ServicePricingService.create_service_pricing(
        db_session,
        ServicePricingCreateRequest(
            service_type_id=service_type.id,
            laundry_item_type_id=item_type.id,
            price=Decimal("50.00"),
        ),
    )

    assert pricing.id is not None
    assert pricing.price == Decimal("50.00")
    assert pricing.is_active is True


def test_retrieve_service_pricing(db_session):
    service_type = _make_service_type(db_session)
    item_type = _make_item_type(db_session)

    created = ServicePricingService.create_service_pricing(
        db_session,
        ServicePricingCreateRequest(
            service_type_id=service_type.id,
            laundry_item_type_id=item_type.id,
            price=Decimal("30.00"),
        ),
    )

    fetched = ServicePricingService.get_pricing_by_id(db_session, created.id)
    assert fetched.id == created.id


def test_update_service_pricing(db_session):
    service_type = _make_service_type(db_session)
    item_type = _make_item_type(db_session)

    created = ServicePricingService.create_service_pricing(
        db_session,
        ServicePricingCreateRequest(
            service_type_id=service_type.id,
            laundry_item_type_id=item_type.id,
            price=Decimal("30.00"),
        ),
    )

    updated = ServicePricingService.update_service_pricing(
        db_session,
        created.id,
        ServicePricingUpdateRequest(price=Decimal("45.00")),
    )

    assert updated.price == Decimal("45.00")


def test_negative_price_fails_schema_validation():
    with pytest.raises(ValidationError):
        ServicePricingCreateRequest(
            service_type_id=uuid.uuid4(),
            laundry_item_type_id=uuid.uuid4(),
            price=Decimal("-1.00"),
        )


def test_duplicate_service_item_combination_fails(db_session):
    service_type = _make_service_type(db_session)
    item_type = _make_item_type(db_session)

    payload = ServicePricingCreateRequest(
        service_type_id=service_type.id,
        laundry_item_type_id=item_type.id,
        price=Decimal("20.00"),
    )
    ServicePricingService.create_service_pricing(db_session, payload)

    with pytest.raises(ConflictError):
        ServicePricingService.create_service_pricing(db_session, payload)


def test_missing_service_type_fails(db_session):
    item_type = _make_item_type(db_session)

    with pytest.raises(NotFoundError):
        ServicePricingService.create_service_pricing(
            db_session,
            ServicePricingCreateRequest(
                service_type_id=uuid.uuid4(),
                laundry_item_type_id=item_type.id,
                price=Decimal("20.00"),
            ),
        )


def test_missing_item_type_fails(db_session):
    service_type = _make_service_type(db_session)

    with pytest.raises(NotFoundError):
        ServicePricingService.create_service_pricing(
            db_session,
            ServicePricingCreateRequest(
                service_type_id=service_type.id,
                laundry_item_type_id=uuid.uuid4(),
                price=Decimal("20.00"),
            ),
        )


def test_inactive_service_type_blocks_new_pricing(db_session):
    service_type = _make_service_type(db_session)
    item_type = _make_item_type(db_session)

    ServiceTypeService.update_service_type(
        db_session, service_type.id, ServiceTypeUpdateRequest(is_active=False)
    )

    with pytest.raises(ConflictError):
        ServicePricingService.create_service_pricing(
            db_session,
            ServicePricingCreateRequest(
                service_type_id=service_type.id,
                laundry_item_type_id=item_type.id,
                price=Decimal("20.00"),
            ),
        )


def test_inactive_item_type_blocks_new_pricing(db_session):
    service_type = _make_service_type(db_session)
    item_type = _make_item_type(db_session)

    LaundryItemTypeService.update_laundry_item_type(
        db_session, item_type.id, LaundryItemTypeUpdateRequest(is_active=False)
    )

    with pytest.raises(ConflictError):
        ServicePricingService.create_service_pricing(
            db_session,
            ServicePricingCreateRequest(
                service_type_id=service_type.id,
                laundry_item_type_id=item_type.id,
                price=Decimal("20.00"),
            ),
        )


def test_get_items_for_service_returns_prices(db_session):
    service_type = _make_service_type(db_session)
    shirt = _make_item_type(db_session, name="Shirt")
    pant = _make_item_type(db_session, name="Pant")

    ServicePricingService.create_service_pricing(
        db_session,
        ServicePricingCreateRequest(
            service_type_id=service_type.id, laundry_item_type_id=shirt.id, price=Decimal("50.00")
        ),
    )
    ServicePricingService.create_service_pricing(
        db_session,
        ServicePricingCreateRequest(
            service_type_id=service_type.id, laundry_item_type_id=pant.id, price=Decimal("70.00")
        ),
    )

    results = ServicePricingService.get_items_for_service(db_session, service_type.id)
    prices_by_name = {r.name: r.price for r in results}

    assert prices_by_name["Shirt"] == Decimal("50.00")
    assert prices_by_name["Pant"] == Decimal("70.00")
