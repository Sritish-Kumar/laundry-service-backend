import uuid

from app.core.constants import UserRole
from app.core.security import create_access_token


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


def _signup(client, role="CUSTOMER", **overrides):
    payload = _signup_payload(role=role, **overrides)
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    return payload, response.json()["data"]


def _auth_headers(token_data):
    return {
        "Authorization": f"Bearer {token_data['access_token']}",
    }


def _assert_unauthorized(response):
    assert response.status_code == 401
    data = response.json()
    if "success" in data:
        assert data["success"] is False
        assert data["data"] is None


def test_get_me_returns_current_user(client):
    signup_payload, token_data = _signup(client, role="CUSTOMER")

    response = client.get(
        "/users/me",
        headers=_auth_headers(token_data),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == signup_payload["full_name"]
    assert data["email"] == signup_payload["email"]
    assert data["phone"] == signup_payload["phone"]
    assert data["role"] == signup_payload["role"]
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_get_me_requires_access_token(client):
    response = client.get("/users/me")

    _assert_unauthorized(response)


def test_get_me_with_invalid_access_token_returns_401(client):
    _, token_data = _signup(client)
    access_token = token_data["access_token"]
    header, payload, signature = access_token.split(".")
    replacement_char = "a" if signature[0] != "a" else "b"
    modified_access_token = f"{header}.{payload}.{replacement_char}{signature[1:]}"

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {modified_access_token}"},
    )

    _assert_unauthorized(response)


def test_get_me_with_missing_user_returns_401(client):
    access_token = create_access_token(
        user_id=uuid.uuid4(),
        role=UserRole.CUSTOMER,
        session_id=uuid.uuid4(),
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    _assert_unauthorized(response)


def test_get_me_returns_admin_user_role(client):
    signup_payload, token_data = _signup(client, role="ADMIN")

    response = client.get(
        "/users/me",
        headers=_auth_headers(token_data),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == signup_payload["email"]
    assert data["role"] == "ADMIN"
