import uuid


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
    response = client.post(
        "/auth/signup",
        json=_signup_payload(role=role, **overrides),
    )
    assert response.status_code == 201
    return response.json()["data"]


def _auth_headers(token_data):
    return {
        "Authorization": f"Bearer {token_data['access_token']}",
    }


def _service_type_payload(**overrides):
    payload = {
        "name": f"Wash & Fold {uuid.uuid4().hex[:8]}",
        "description": "Standard laundry wash and fold service",
        "current_price": "12.50",
    }
    payload.update(overrides)
    return payload


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
    assert data["current_price"] == payload["current_price"]
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
    payload = _service_type_payload(
        name="A",
        current_price="0",
    )

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
    assert (
        service_types_by_name[first_payload["name"]]["current_price"]
        == first_payload["current_price"]
    )
    assert (
        service_types_by_name[second_payload["name"]]["current_price"]
        == second_payload["current_price"]
    )
