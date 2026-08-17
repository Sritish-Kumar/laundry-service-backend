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


# ---------- Creation ----------


def test_create_normal_address(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    response = client.post(
        "/users/me/addresses",
        json=_address_payload(label="Home"),
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["label"] == "Home"
    assert data["is_default"] is False
    assert data["recipient_name"] == "Jane Doe"
    assert data["latitude"] == "39.781721"
    assert data["longitude"] == "-89.650148"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_default_address(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    address = _create_address(client, headers, label="Home", is_default=True)

    assert address["is_default"] is True


def test_create_second_address(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    _create_address(client, headers, label="Home")
    second = _create_address(client, headers, label="Office")

    list_response = client.get("/users/me/addresses", headers=headers)
    assert list_response.status_code == 200
    addresses = list_response.json()["data"]
    assert len(addresses) == 2
    labels = {a["label"] for a in addresses}
    assert labels == {"Home", "Office"}
    assert second["label"] == "Office"


# ---------- Default behavior ----------


def test_first_address_can_be_default(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    address = _create_address(client, headers, label="Home", is_default=True)

    assert address["is_default"] is True


def test_creating_another_default_removes_previous_default(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    home = _create_address(client, headers, label="Home", is_default=True)
    office = _create_address(client, headers, label="Office", is_default=True)

    list_response = client.get("/users/me/addresses", headers=headers)
    addresses = {a["label"]: a for a in list_response.json()["data"]}

    assert addresses["Office"]["is_default"] is True
    assert addresses["Home"]["is_default"] is False
    assert office["is_default"] is True
    assert home["id"] != office["id"]


def test_updating_address_to_default_removes_previous_default(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    home = _create_address(client, headers, label="Home", is_default=True)
    office = _create_address(client, headers, label="Office", is_default=False)

    patch_response = client.patch(
        f"/users/me/addresses/{office['id']}",
        json={"is_default": True},
        headers=headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["is_default"] is True

    list_response = client.get("/users/me/addresses", headers=headers)
    addresses = {a["label"]: a for a in list_response.json()["data"]}

    assert addresses["Office"]["is_default"] is True
    assert addresses["Home"]["is_default"] is False


def test_user_can_have_zero_defaults(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    _create_address(client, headers, label="Home", is_default=False)
    _create_address(client, headers, label="Office", is_default=False)

    list_response = client.get("/users/me/addresses", headers=headers)
    addresses = list_response.json()["data"]

    assert all(a["is_default"] is False for a in addresses)


# ---------- Coordinate validation ----------


def test_invalid_latitude_longitude_rejected(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    response = client.post(
        "/users/me/addresses",
        json=_address_payload(latitude="250", longitude="500"),
        headers=headers,
    )

    assert response.status_code == 422


def test_negative_location_accuracy_rejected(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    response = client.post(
        "/users/me/addresses",
        json=_address_payload(location_accuracy="-1"),
        headers=headers,
    )

    assert response.status_code == 422


# ---------- Ownership ----------


def test_user_cannot_get_update_or_delete_another_users_address(client):
    user_a_token = _signup(client)
    user_b_token = _signup(client)

    headers_a = _auth_headers(user_a_token)
    headers_b = _auth_headers(user_b_token)

    address_b = _create_address(client, headers_b, label="Bob's Home")

    get_response = client.get("/users/me/addresses", headers=headers_a)
    assert get_response.status_code == 200
    assert get_response.json()["data"] == []

    patch_response = client.patch(
        f"/users/me/addresses/{address_b['id']}",
        json={"label": "Hacked"},
        headers=headers_a,
    )
    assert patch_response.status_code == 404
    patch_body = patch_response.json()
    assert patch_body["success"] is False
    assert patch_body["data"] is None

    delete_response = client.delete(
        f"/users/me/addresses/{address_b['id']}",
        headers=headers_a,
    )
    assert delete_response.status_code == 404

    # confirm address B is untouched
    list_response_b = client.get("/users/me/addresses", headers=headers_b)
    addresses_b = list_response_b.json()["data"]
    assert len(addresses_b) == 1
    assert addresses_b[0]["label"] == "Bob's Home"


def test_get_or_modify_nonexistent_address_returns_404(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    fake_id = uuid.uuid4()

    patch_response = client.patch(
        f"/users/me/addresses/{fake_id}",
        json={"label": "Nowhere"},
        headers=headers,
    )
    assert patch_response.status_code == 404

    delete_response = client.delete(
        f"/users/me/addresses/{fake_id}",
        headers=headers,
    )
    assert delete_response.status_code == 404


# ---------- Update ----------


def test_update_address_fields(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    address = _create_address(client, headers, label="Home")

    response = client.patch(
        f"/users/me/addresses/{address['id']}",
        json={
            "label": "Home Updated",
            "city": "Chicago",
            "recipient_name": "John Smith",
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["label"] == "Home Updated"
    assert data["city"] == "Chicago"
    assert data["recipient_name"] == "John Smith"
    # untouched fields remain
    assert data["state"] == "IL"


def test_partial_update_works(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    address = _create_address(client, headers, label="Home")

    response = client.patch(
        f"/users/me/addresses/{address['id']}",
        json={"landmark": "Near the school"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["landmark"] == "Near the school"
    assert data["label"] == "Home"
    assert data["address_line_1"] == "123 Main St"


def test_update_coordinates(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    address = _create_address(client, headers, label="Home")

    response = client.patch(
        f"/users/me/addresses/{address['id']}",
        json={"latitude": "10.123456", "longitude": "20.654321"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["latitude"] == "10.123456"
    assert data["longitude"] == "20.654321"


def test_change_default_status(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    address = _create_address(client, headers, label="Home", is_default=True)

    response = client.patch(
        f"/users/me/addresses/{address['id']}",
        json={"is_default": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["is_default"] is False


# ---------- Delete ----------


def test_delete_normal_address(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    address = _create_address(client, headers, label="Home")

    response = client.delete(f"/users/me/addresses/{address['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

    list_response = client.get("/users/me/addresses", headers=headers)
    assert list_response.json()["data"] == []


def test_delete_default_address_does_not_promote_another(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    home = _create_address(client, headers, label="Home", is_default=True)
    _create_address(client, headers, label="Office", is_default=False)
    _create_address(client, headers, label="Hostel", is_default=False)

    response = client.delete(f"/users/me/addresses/{home['id']}", headers=headers)
    assert response.status_code == 200

    list_response = client.get("/users/me/addresses", headers=headers)
    addresses = list_response.json()["data"]

    assert len(addresses) == 2
    assert all(a["is_default"] is False for a in addresses)


def test_existing_addresses_remain_untouched_after_delete(client):
    token_data = _signup(client)
    headers = _auth_headers(token_data)

    home = _create_address(client, headers, label="Home")
    office = _create_address(client, headers, label="Office", city="Metropolis")

    client.delete(f"/users/me/addresses/{home['id']}", headers=headers)

    list_response = client.get("/users/me/addresses", headers=headers)
    addresses = list_response.json()["data"]

    assert len(addresses) == 1
    assert addresses[0]["id"] == office["id"]
    assert addresses[0]["city"] == "Metropolis"
