import uuid

import pytest

from app.exceptions.custom_exceptions import ConflictError, NotFoundError
from app.schemas.laundry_item_type import (
    LaundryItemTypeCreateRequest,
    LaundryItemTypeUpdateRequest,
)
from app.services.laundry_item_type_service import LaundryItemTypeService


def _payload(**overrides):
    payload = {
        "name": f"Shirt {uuid.uuid4().hex[:8]}",
        "description": "A standard shirt",
    }
    payload.update(overrides)
    return LaundryItemTypeCreateRequest(**payload)


def test_create_laundry_item_type(db_session):
    item_type = LaundryItemTypeService.create_laundry_item_type(db_session, _payload())

    assert item_type.id is not None
    assert item_type.is_active is True


def test_duplicate_laundry_item_type_name_fails(db_session):
    payload = _payload(name="Jeans")
    LaundryItemTypeService.create_laundry_item_type(db_session, payload)

    with pytest.raises(ConflictError):
        LaundryItemTypeService.create_laundry_item_type(db_session, payload)


def test_update_laundry_item_type(db_session):
    item_type = LaundryItemTypeService.create_laundry_item_type(db_session, _payload(name="Blanket"))

    updated = LaundryItemTypeService.update_laundry_item_type(
        db_session,
        item_type.id,
        LaundryItemTypeUpdateRequest(name="Winter Blanket", is_active=False),
    )

    assert updated.name == "Winter Blanket"
    assert updated.is_active is False


def test_update_to_duplicate_name_fails(db_session):
    LaundryItemTypeService.create_laundry_item_type(db_session, _payload(name="Curtain"))
    other = LaundryItemTypeService.create_laundry_item_type(db_session, _payload(name="Bedsheet"))

    with pytest.raises(ConflictError):
        LaundryItemTypeService.update_laundry_item_type(
            db_session,
            other.id,
            LaundryItemTypeUpdateRequest(name="Curtain"),
        )


def test_update_nonexistent_laundry_item_type_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        LaundryItemTypeService.update_laundry_item_type(
            db_session,
            uuid.uuid4(),
            LaundryItemTypeUpdateRequest(name="Does Not Matter"),
        )


def test_inactive_laundry_item_type_still_retrievable(db_session):
    item_type = LaundryItemTypeService.create_laundry_item_type(db_session, _payload(name="Towel"))

    LaundryItemTypeService.update_laundry_item_type(
        db_session,
        item_type.id,
        LaundryItemTypeUpdateRequest(is_active=False),
    )

    fetched = LaundryItemTypeService.get_laundry_item_type(db_session, item_type.id)
    assert fetched.is_active is False
