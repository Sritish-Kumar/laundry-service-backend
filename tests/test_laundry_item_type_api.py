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


def test_admin_can_create_item_type(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    payload = _item_type_payload()

    response = client.post("/item-types", json=payload, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["is_active"] is True
    assert "id" in data


def test_create_item_type_requires_access_token(client):
    response = client.post("/item-types", json=_item_type_payload())

    assert response.status_code == 401


def test_customer_cannot_create_item_type(client):
    customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))

    response = client.post(
        "/item-types", json=_item_type_payload(), headers=customer_headers
    )

    assert response.status_code == 403


def test_create_item_type_validates_payload(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))

    response = client.post(
        "/item-types", json=_item_type_payload(name="A"), headers=admin_headers
    )

    assert response.status_code == 422


def test_duplicate_item_type_name_is_rejected(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    payload = _item_type_payload(name="Jeans")

    first = client.post("/item-types", json=payload, headers=admin_headers)
    assert first.status_code == 200

    second = client.post("/item-types", json=payload, headers=admin_headers)
    assert second.status_code == 409


def test_get_all_item_types_returns_empty_list(client):
    response = client.get("/item-types")

    assert response.status_code == 200
    assert response.json() == []


def test_get_all_item_types_returns_created_item_types(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    _create_item_type(client, admin_headers, name="Shirt")
    _create_item_type(client, admin_headers, name="Pant")

    response = client.get("/item-types")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert names == {"Shirt", "Pant"}


def test_get_item_type_returns_active_item(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    created = _create_item_type(client, admin_headers, name="Blanket")

    response = client.get(f"/item-types/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Blanket"


def test_get_item_type_returns_404_for_nonexistent(client):
    response = client.get(f"/item-types/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_item_type_returns_404_for_inactive(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    created = _create_item_type(client, admin_headers, name="Curtain")

    patch_response = client.patch(
        f"/item-types/{created['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert patch_response.status_code == 200

    response = client.get(f"/item-types/{created['id']}")
    assert response.status_code == 404


def test_admin_can_update_item_type(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    created = _create_item_type(client, admin_headers, name="Towel")

    response = client.patch(
        f"/item-types/{created['id']}",
        json={"name": "Bath Towel", "description": "Updated"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bath Towel"
    assert data["description"] == "Updated"


def test_customer_cannot_update_item_type(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
    created = _create_item_type(client, admin_headers, name="Winter Wear")

    response = client.patch(
        f"/item-types/{created['id']}",
        json={"description": "hijacked"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_update_item_type_to_duplicate_name_is_rejected(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    _create_item_type(client, admin_headers, name="Shirt")
    pant = _create_item_type(client, admin_headers, name="Pant")

    response = client.patch(
        f"/item-types/{pant['id']}",
        json={"name": "Shirt"},
        headers=admin_headers,
    )

    assert response.status_code == 409


def test_update_nonexistent_item_type_returns_404(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))

    response = client.patch(
        f"/item-types/{uuid.uuid4()}",
        json={"description": "Does not matter"},
        headers=admin_headers,
    )

    assert response.status_code == 404
