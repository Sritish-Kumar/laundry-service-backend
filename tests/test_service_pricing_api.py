import uuid
from datetime import UTC, datetime

from app.repo.user_repo import UserRepository
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


def _create_service_type(client, admin_headers, **overrides):
    payload = {
        "name": f"Wash {uuid.uuid4().hex[:8]}",
        "description": "A wash service",
    }
    payload.update(overrides)

    response = client.post("/service-types", json=payload, headers=admin_headers)
    assert response.status_code == 200
    return response.json()


def _create_item_type(client, admin_headers, **overrides):
    payload = {
        "name": f"Shirt {uuid.uuid4().hex[:8]}",
        "description": "A standard shirt",
    }
    payload.update(overrides)

    response = client.post("/item-types", json=payload, headers=admin_headers)
    assert response.status_code == 200
    return response.json()


def _pricing_payload(service_type_id, laundry_item_type_id, price="50.00"):
    return {
        "service_type_id": service_type_id,
        "laundry_item_type_id": laundry_item_type_id,
        "price": price,
    }


def _setup_service_and_item(client, admin_headers):
    service_type = _create_service_type(client, admin_headers)
    item_type = _create_item_type(client, admin_headers)
    return service_type, item_type


def test_admin_can_create_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    response = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"], "50.00"),
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["service_type_id"] == service_type["id"]
    assert data["laundry_item_type_id"] == item_type["id"]
    assert data["price"] == "50.00"
    assert data["is_active"] is True


def test_create_pricing_requires_access_token(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    response = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"]),
    )

    assert response.status_code == 401


def test_customer_cannot_create_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    response = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"]),
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_admin_can_get_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    created = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"]),
        headers=admin_headers,
    ).json()

    response = client.get(f"/service-pricing/{created['id']}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_customer_cannot_get_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    created = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"]),
        headers=admin_headers,
    ).json()

    response = client.get(f"/service-pricing/{created['id']}", headers=customer_headers)

    assert response.status_code == 403


def test_get_nonexistent_pricing_returns_404(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))

    response = client.get(f"/service-pricing/{uuid.uuid4()}", headers=admin_headers)

    assert response.status_code == 404


def test_admin_can_update_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    created = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"], "50.00"),
        headers=admin_headers,
    ).json()

    response = client.patch(
        f"/service-pricing/{created['id']}",
        json={"price": "60.00"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["price"] == "60.00"


def test_customer_cannot_update_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    created = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"]),
        headers=admin_headers,
    ).json()

    response = client.patch(
        f"/service-pricing/{created['id']}",
        json={"price": "1.00"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_duplicate_service_item_combination_is_rejected(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    payload = _pricing_payload(service_type["id"], item_type["id"])
    first = client.post("/service-pricing", json=payload, headers=admin_headers)
    assert first.status_code == 200

    second = client.post("/service-pricing", json=payload, headers=admin_headers)
    assert second.status_code == 409


def test_pricing_with_missing_service_returns_404(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    _, item_type = _setup_service_and_item(client, admin_headers)

    response = client.post(
        "/service-pricing",
        json=_pricing_payload(str(uuid.uuid4()), item_type["id"]),
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_pricing_with_missing_item_type_returns_404(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    service_type, _ = _setup_service_and_item(client, admin_headers)

    response = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], str(uuid.uuid4())),
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_negative_price_returns_422(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    service_type, item_type = _setup_service_and_item(client, admin_headers)

    response = client.post(
        "/service-pricing",
        json=_pricing_payload(service_type["id"], item_type["id"], "-5.00"),
        headers=admin_headers,
    )

    assert response.status_code == 422
