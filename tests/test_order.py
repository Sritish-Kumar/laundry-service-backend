import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.core.constants import OrderStatus
from app.models.order_status_history import OrderStatusHistory
from app.models.service_type import ServiceType
from app.repo.user_repo import UserRepository
from app.schemas.laundry_item_type import LaundryItemTypeCreateRequest, LaundryItemTypeUpdateRequest
from app.schemas.service_pricing import ServicePricingCreateRequest, ServicePricingUpdateRequest
from app.services.laundry_item_type_service import LaundryItemTypeService
from app.services.service_pricing_service import ServicePricingService
from tests.conftest import TestingSessionLocal


def _signup_payload(role="CUSTOMER", **overrides):
    unique_id = uuid.uuid4().hex
    phone_suffix = uuid.uuid4().int % 10000000
    payload = {
        "full_name": f"{role.title()} User",
        "email": f"{role.lower()}-{unique_id}@example.com",
        "phone": f"555{phone_suffix:07d}",
        "password": "password123",
        "role": role,
    }
    payload.update(overrides)
    return payload


def _mark_user_verified(email: str) -> None:
    db = TestingSessionLocal()
    try:
        user = UserRepository.get_user_by_email(db, email)
        if user is not None:
            user.is_email_verified = True
            user.email_verified_at = datetime.now(UTC)
            db.commit()
    finally:
        db.close()


def _signup(client, role="CUSTOMER", **overrides):
    payload = _signup_payload(role=role, **overrides)
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201

    _mark_user_verified(payload["email"])

    login_response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    return login_response.json()["data"]


def _auth_headers(token_data):
    return {"Authorization": f"Bearer {token_data['access_token']}"}


def _address_payload(**overrides):
    payload = {
        "label": "Home",
        "is_default": False,
        "recipient_name": "Jane Doe",
        "recipient_phone": f"555{uuid.uuid4().int % 10000000:07d}",
        "address_line_1": "123 Main St",
        "address_line_2": "Apt 4B",
        "landmark": "Near the park",
        "city": "Springfield",
        "state": "IL",
        "postal_code": "62704",
        "country": "USA",
        "latitude": "39.781721",
        "longitude": "-89.650148",
        "location_accuracy": "5.0",
    }
    payload.update(overrides)
    return payload


def _create_address(client, headers, **overrides):
    response = client.post(
        "/users/me/addresses",
        json=_address_payload(**overrides),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["data"]


def _service_type_payload(**overrides):
    payload = {
        "name": f"Wash & Fold {uuid.uuid4().hex[:8]}",
        "description": "Standard laundry wash and fold service",
    }
    payload.update(overrides)
    return payload


def _create_service_type(client, admin_headers, **overrides):
    response = client.post(
        "/service-types",
        json=_service_type_payload(**overrides),
        headers=admin_headers,
    )
    assert response.status_code == 200
    return response.json()


def _deactivate_service_type(service_type_id: str) -> None:
    db = TestingSessionLocal()
    try:
        service_type = (
            db.query(ServiceType)
            .filter(ServiceType.id == uuid.UUID(service_type_id))
            .first()
        )
        assert service_type is not None
        service_type.is_active = False
        db.commit()
    finally:
        db.close()


def _create_laundry_item_type(**overrides):
    db = TestingSessionLocal()
    try:
        payload = LaundryItemTypeCreateRequest(
            name=overrides.pop("name", f"Shirt {uuid.uuid4().hex[:8]}"),
            **overrides,
        )
        item_type = LaundryItemTypeService.create_laundry_item_type(db, payload)
        return {"id": str(item_type.id), "name": item_type.name}
    finally:
        db.close()


def _create_service_pricing(service_type_id, laundry_item_type_id, price="12.50"):
    db = TestingSessionLocal()
    try:
        payload = ServicePricingCreateRequest(
            service_type_id=uuid.UUID(service_type_id),
            laundry_item_type_id=uuid.UUID(laundry_item_type_id),
            price=Decimal(price),
        )
        pricing = ServicePricingService.create_service_pricing(db, payload)
        return {"id": str(pricing.id), "price": str(pricing.price)}
    finally:
        db.close()


def _update_service_pricing_price(pricing_id: str, price: str) -> None:
    db = TestingSessionLocal()
    try:
        ServicePricingService.update_service_pricing(
            db,
            uuid.UUID(pricing_id),
            ServicePricingUpdateRequest(price=Decimal(price)),
        )
    finally:
        db.close()


def _order_payload(address_id, service_type_id, laundry_item_type_id, **overrides):
    payload = {
        "address_id": address_id,
        "pickup_date": "2026-08-20",
        "pickup_slot": "10:00-12:00",
        "items": [
            {
                "laundry_item_type_id": laundry_item_type_id,
                "quantity": 3,
                "service_type_id": service_type_id,
            }
        ],
    }
    payload.update(overrides)
    return payload


def _setup_customer_with_address_and_service(client):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = _auth_headers(customer_token)

    address = _create_address(client, customer_headers, label="Home")
    service_type = _create_service_type(client, _auth_headers(admin_token))
    item_type = _create_laundry_item_type()
    pricing = _create_service_pricing(service_type["id"], item_type["id"])

    return customer_headers, address, service_type, item_type, pricing


# ---------- Successful creation ----------


def test_authenticated_customer_can_create_order(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "PENDING_PICKUP"
    assert "id" in data
    assert data["public_order_number"].startswith("ORD-")


def test_address_snapshot_is_copied_correctly(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]

    for field in [
        "recipient_name",
        "recipient_phone",
        "address_line_1",
        "address_line_2",
        "landmark",
        "city",
        "state",
        "postal_code",
        "country",
        "latitude",
        "longitude",
    ]:
        assert data[field] == address[field], field


def test_initial_status_history_row_exists(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )
    order_id = response.json()["data"]["id"]

    db = TestingSessionLocal()
    try:
        history_rows = (
            db.query(OrderStatusHistory)
            .filter(OrderStatusHistory.order_id == uuid.UUID(order_id))
            .all()
        )
        assert len(history_rows) == 1
        assert history_rows[0].status == OrderStatus.PENDING_PICKUP
    finally:
        db.close()


def test_laundry_items_price_and_total_are_correct(client):
    customer_headers, address, service_type, shirt_type, shirt_pricing = (
        _setup_customer_with_address_and_service(client)
    )

    pants_type = _create_laundry_item_type(name=f"Pants {uuid.uuid4().hex[:8]}")
    _create_service_pricing(service_type["id"], pants_type["id"], price="10.00")

    response = client.post(
        "/orders/",
        json=_order_payload(
            address["id"],
            service_type["id"],
            shirt_type["id"],
            items=[
                {
                    "laundry_item_type_id": shirt_type["id"],
                    "quantity": 3,
                    "service_type_id": service_type["id"],
                },
                {
                    "laundry_item_type_id": pants_type["id"],
                    "quantity": 2,
                    "service_type_id": service_type["id"],
                },
            ],
        ),
        headers=customer_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    items = data["items"]
    assert len(items) == 2

    shirt = next(i for i in items if i["item_type_name_snapshot"] == shirt_type["name"])
    pants = next(i for i in items if i["item_type_name_snapshot"] == pants_type["name"])

    assert shirt["service_price_snapshot"] == shirt_pricing["price"]
    assert shirt["item_total_price"] == "37.50"
    assert pants["item_total_price"] == "20.00"
    assert data["total_price"] == "57.50"


# ---------- Address behavior ----------


def test_customer_can_order_using_home_address(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["city"] == address["city"]


def test_customer_can_order_using_office_address(client):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = _auth_headers(customer_token)

    _create_address(client, customer_headers, label="Home")
    office = _create_address(client, customer_headers, label="Office", city="Metropolis")
    service_type = _create_service_type(client, _auth_headers(admin_token))
    item_type = _create_laundry_item_type()
    _create_service_pricing(service_type["id"], item_type["id"])

    response = client.post(
        "/orders/",
        json=_order_payload(office["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["city"] == "Metropolis"


def test_order_creation_with_another_users_address_returns_404(client):
    admin_token = _signup(client, role="ADMIN")
    user_a_token = _signup(client, role="CUSTOMER")
    user_b_token = _signup(client, role="CUSTOMER")

    headers_a = _auth_headers(user_a_token)
    headers_b = _auth_headers(user_b_token)

    address_b = _create_address(client, headers_b, label="Bob's Home")
    service_type = _create_service_type(client, _auth_headers(admin_token))
    item_type = _create_laundry_item_type()
    _create_service_pricing(service_type["id"], item_type["id"])

    response = client.post(
        "/orders/",
        json=_order_payload(address_b["id"], service_type["id"], item_type["id"]),
        headers=headers_a,
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None


def test_order_creation_with_nonexistent_address_returns_404(client):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = _auth_headers(customer_token)

    service_type = _create_service_type(client, _auth_headers(admin_token))
    item_type = _create_laundry_item_type()
    _create_service_pricing(service_type["id"], item_type["id"])

    response = client.post(
        "/orders/",
        json=_order_payload(str(uuid.uuid4()), service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 404


def test_editing_or_deleting_address_does_not_change_existing_order_snapshot(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    create_response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )
    order_id = create_response.json()["data"]["id"]

    patch_response = client.patch(
        f"/users/me/addresses/{address['id']}",
        json={"city": "New City"},
        headers=customer_headers,
    )
    assert patch_response.status_code == 200

    order_after_edit = client.get(f"/orders/{order_id}", headers=customer_headers)
    assert order_after_edit.status_code == 200
    assert order_after_edit.json()["city"] == "Springfield"

    delete_response = client.delete(
        f"/users/me/addresses/{address['id']}",
        headers=customer_headers,
    )
    assert delete_response.status_code == 200

    order_after_delete = client.get(f"/orders/{order_id}", headers=customer_headers)
    assert order_after_delete.status_code == 200
    assert order_after_delete.json()["city"] == "Springfield"


# ---------- Service behavior ----------


def test_order_creation_with_nonexistent_service_type_returns_404(client):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = _auth_headers(customer_token)

    address = _create_address(client, customer_headers, label="Home")

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], str(uuid.uuid4()), str(uuid.uuid4())),
        headers=customer_headers,
    )

    assert response.status_code == 404


def test_order_creation_with_inactive_service_type_returns_409(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    _deactivate_service_type(service_type["id"])

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 409


def test_order_creation_with_nonexistent_item_type_returns_404(client):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = _auth_headers(customer_token)

    address = _create_address(client, customer_headers, label="Home")
    service_type = _create_service_type(client, _auth_headers(admin_token))

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], str(uuid.uuid4())),
        headers=customer_headers,
    )

    assert response.status_code == 404


def test_order_creation_with_inactive_item_type_returns_409(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    db = TestingSessionLocal()
    try:
        LaundryItemTypeService.update_laundry_item_type(
            db,
            uuid.UUID(item_type["id"]),
            LaundryItemTypeUpdateRequest(is_active=False),
        )
    finally:
        db.close()

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 409


def test_order_creation_with_no_pricing_for_combination_returns_404(client):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = _auth_headers(customer_token)

    address = _create_address(client, customer_headers, label="Home")
    service_type = _create_service_type(client, _auth_headers(admin_token))
    item_type = _create_laundry_item_type()
    # deliberately no ServicePricing created for this service + item combination

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 404


def test_order_price_is_resolved_from_service_pricing(client):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = _auth_headers(customer_token)

    address = _create_address(client, customer_headers, label="Home")
    service_type = _create_service_type(client, _auth_headers(admin_token), name="Wash")
    item_type = _create_laundry_item_type(name="Shirt")
    _create_service_pricing(service_type["id"], item_type["id"], price="50.00")

    response = client.post(
        "/orders/",
        json=_order_payload(
            address["id"],
            service_type["id"],
            item_type["id"],
            items=[
                {
                    "laundry_item_type_id": item_type["id"],
                    "quantity": 3,
                    "service_type_id": service_type["id"],
                }
            ],
        ),
        headers=customer_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["items"][0]["service_price_snapshot"] == "50.00"
    assert data["items"][0]["item_total_price"] == "150.00"
    assert data["total_price"] == "150.00"


def test_updating_pricing_later_does_not_change_existing_order_snapshot(client):
    customer_headers, address, service_type, item_type, pricing = _setup_customer_with_address_and_service(client)

    create_response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["data"]["id"]

    _update_service_pricing_price(pricing["id"], "99.99")

    order_response = client.get(f"/orders/{order_id}", headers=customer_headers)
    assert order_response.status_code == 200
    item = order_response.json()["items"][0]
    assert item["service_price_snapshot"] == pricing["price"]
    assert item["item_total_price"] == "37.50"


def test_client_supplied_price_is_ignored(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    payload = _order_payload(address["id"], service_type["id"], item_type["id"])
    payload["total_price"] = "1.00"
    payload["items"][0]["price"] = "1.00"
    payload["items"][0]["service_price_snapshot"] = "1.00"

    response = client.post("/orders/", json=payload, headers=customer_headers)

    assert response.status_code == 201
    data = response.json()["data"]
    # 3 * 12.50, computed server-side from ServicePricing
    assert data["total_price"] == "37.50"
    assert data["items"][0]["item_total_price"] == "37.50"


# ---------- Transaction behavior ----------


def test_failed_order_creation_persists_nothing(client):
    customer_headers, address, service_type, item_type, _pricing = _setup_customer_with_address_and_service(client)

    response = client.post(
        "/orders/",
        json=_order_payload(
            address["id"],
            service_type["id"],
            item_type["id"],
            items=[
                {
                    "laundry_item_type_id": item_type["id"],
                    "quantity": 1,
                    "service_type_id": service_type["id"],
                },
                {
                    "laundry_item_type_id": item_type["id"],
                    "quantity": 1,
                    "service_type_id": str(uuid.uuid4()),
                },
            ],
        ),
        headers=customer_headers,
    )

    assert response.status_code == 404

    list_response = client.get("/orders/", headers=customer_headers)
    assert list_response.status_code == 404


# ---------- Authentication ----------


def test_order_creation_requires_authentication(client):
    response = client.post(
        "/orders/",
        json=_order_payload(str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())),
    )

    assert response.status_code == 401
