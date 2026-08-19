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
    return {
        "Authorization": f"Bearer {token_data['access_token']}",
    }


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


def _item_type_payload(**overrides):
    payload = {
        "name": f"Shirt {uuid.uuid4().hex[:8]}",
        "description": "A standard shirt",
    }
    payload.update(overrides)
    return payload


def _create_item_type(client, admin_headers, **overrides):
    response = client.post(
        "/item-types",
        json=_item_type_payload(**overrides),
        headers=admin_headers,
    )
    assert response.status_code == 200
    return response.json()


def _create_pricing(client, admin_headers, service_type_id, item_type_id, price="12.50"):
    response = client.post(
        "/service-pricing",
        json={
            "service_type_id": service_type_id,
            "laundry_item_type_id": item_type_id,
            "price": price,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    return response.json()


def test_admin_can_create_service_type(client):
    admin_token_data = _signup(client, role="ADMIN")
    payload = _service_type_payload()

    response = client.post(
        "/service-types",
        json=payload,
        headers=_auth_headers(admin_token_data),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


def test_create_service_type_requires_access_token(client):
    response = client.post(
        "/service-types",
        json=_service_type_payload(),
    )

    assert response.status_code == 401


def test_customer_cannot_create_service_type(client):
    customer_token_data = _signup(client, role="CUSTOMER")

    response = client.post(
        "/service-types",
        json=_service_type_payload(),
        headers=_auth_headers(customer_token_data),
    )

    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["data"] is None


def test_create_service_type_validates_payload(client):
    admin_token_data = _signup(client, role="ADMIN")
    payload = _service_type_payload(name="A")

    response = client.post(
        "/service-types",
        json=payload,
        headers=_auth_headers(admin_token_data),
    )

    assert response.status_code == 422


def test_get_all_service_types_returns_empty_list(client):
    response = client.get("/service-types")

    assert response.status_code == 200
    assert response.json() == []


def test_get_all_service_types_returns_created_service_types(client):
    admin_token_data = _signup(client, role="ADMIN")
    first_payload = _service_type_payload(name="Wash Only")
    second_payload = _service_type_payload(name="Dry Clean")

    first_response = client.post(
        "/service-types",
        json=first_payload,
        headers=_auth_headers(admin_token_data),
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/service-types",
        json=second_payload,
        headers=_auth_headers(admin_token_data),
    )
    assert second_response.status_code == 200

    response = client.get("/service-types")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    service_types_by_name = {item["name"]: item for item in data}
    assert first_payload["name"] in service_types_by_name
    assert second_payload["name"] in service_types_by_name


def test_duplicate_service_type_name_is_rejected(client):
    admin_token_data = _signup(client, role="ADMIN")
    payload = _service_type_payload(name="Duplicate Wash")

    first_response = client.post(
        "/service-types",
        json=payload,
        headers=_auth_headers(admin_token_data),
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/service-types",
        json=payload,
        headers=_auth_headers(admin_token_data),
    )
    assert second_response.status_code == 409


# ---------- Get single service type ----------


def test_get_service_type_returns_active_service(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    created = _create_service_type(client, admin_headers, name="Wash")

    response = client.get(f"/service-types/{created['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["name"] == "Wash"


def test_get_service_type_returns_404_for_nonexistent(client):
    response = client.get(f"/service-types/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_service_type_returns_404_for_inactive(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    created = _create_service_type(client, admin_headers, name="Soon Inactive")

    patch_response = client.patch(
        f"/service-types/{created['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert patch_response.status_code == 200

    response = client.get(f"/service-types/{created['id']}")
    assert response.status_code == 404


# ---------- Update ----------


def test_admin_can_update_service_type(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    created = _create_service_type(client, admin_headers, name="Original Name")

    response = client.patch(
        f"/service-types/{created['id']}",
        json={"name": "Renamed", "description": "Updated description"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Renamed"
    assert data["description"] == "Updated description"


def test_customer_cannot_update_service_type(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
    created = _create_service_type(client, admin_headers, name="Ironing")

    response = client.patch(
        f"/service-types/{created['id']}",
        json={"description": "hijacked"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_update_service_type_to_duplicate_name_is_rejected(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    _create_service_type(client, admin_headers, name="Wash")
    dry_clean = _create_service_type(client, admin_headers, name="Dry Clean")

    response = client.patch(
        f"/service-types/{dry_clean['id']}",
        json={"name": "Wash"},
        headers=admin_headers,
    )

    assert response.status_code == 409


def test_update_nonexistent_service_type_returns_404(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))

    response = client.patch(
        f"/service-types/{uuid.uuid4()}",
        json={"description": "Does not matter"},
        headers=admin_headers,
    )

    assert response.status_code == 404


# ---------- Items available for a service ----------


def test_get_items_for_service_returns_active_prices(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    wash = _create_service_type(client, admin_headers, name="Wash")
    shirt = _create_item_type(client, admin_headers, name="Shirt")
    pant = _create_item_type(client, admin_headers, name="Pant")
    _create_pricing(client, admin_headers, wash["id"], shirt["id"], price="50.00")
    _create_pricing(client, admin_headers, wash["id"], pant["id"], price="70.00")

    response = client.get(f"/service-types/{wash['id']}/items")

    assert response.status_code == 200
    prices_by_name = {item["name"]: item["price"] for item in response.json()}
    assert prices_by_name == {"Shirt": "50.00", "Pant": "70.00"}


def test_get_items_for_service_returns_empty_list_when_no_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    wash = _create_service_type(client, admin_headers, name="Wash")

    response = client.get(f"/service-types/{wash['id']}/items")

    assert response.status_code == 200
    assert response.json() == []


def test_get_items_for_service_returns_404_for_nonexistent_service(client):
    response = client.get(f"/service-types/{uuid.uuid4()}/items")

    assert response.status_code == 404


def test_get_items_for_service_excludes_inactive_pricing(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    wash = _create_service_type(client, admin_headers, name="Wash")
    shirt = _create_item_type(client, admin_headers, name="Shirt")
    pricing = _create_pricing(client, admin_headers, wash["id"], shirt["id"], price="50.00")

    patch_response = client.patch(
        f"/service-pricing/{pricing['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert patch_response.status_code == 200

    response = client.get(f"/service-types/{wash['id']}/items")
    assert response.status_code == 200
    assert response.json() == []


def test_get_items_for_service_excludes_inactive_item_type(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    wash = _create_service_type(client, admin_headers, name="Wash")
    shirt = _create_item_type(client, admin_headers, name="Shirt")
    _create_pricing(client, admin_headers, wash["id"], shirt["id"], price="50.00")

    patch_response = client.patch(
        f"/item-types/{shirt['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert patch_response.status_code == 200

    response = client.get(f"/service-types/{wash['id']}/items")
    assert response.status_code == 200
    assert response.json() == []


def test_get_items_for_service_returns_empty_list_when_service_inactive(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    wash = _create_service_type(client, admin_headers, name="Wash")
    shirt = _create_item_type(client, admin_headers, name="Shirt")
    _create_pricing(client, admin_headers, wash["id"], shirt["id"], price="50.00")

    patch_response = client.patch(
        f"/service-types/{wash['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert patch_response.status_code == 200

    response = client.get(f"/service-types/{wash['id']}/items")
    assert response.status_code == 200
    assert response.json() == []
