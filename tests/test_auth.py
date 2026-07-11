import uuid


def test_signup(client):

    payload = {
        "full_name": "Test User",

        "email": "test@example.com",

        "phone": "9999999999",

        "password": "password123",

        "role": "CUSTOMER"
    }

    response = client.post(
        "/auth/signup",
        json=payload
    )

    if response.status_code != 200:
        print("ERROR RESPONSE:", response.json())
    
    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


def test_signup_duplicate_phone_returns_conflict(client):
    phone = "5550000001"
    first_payload = {
        "full_name": "First User",
        "email": f"first-{uuid.uuid4().hex}@example.com",
        "phone": phone,
        "password": "password123",
        "role": "CUSTOMER"
    }

    first_response = client.post("/auth/signup", json=first_payload)
    assert first_response.status_code == 200

    duplicate_payload = {
        "full_name": "Second User",
        "email": f"second-{uuid.uuid4().hex}@example.com",
        "phone": phone,
        "password": "password123",
        "role": "CUSTOMER"
    }

    response = client.post("/auth/signup", json=duplicate_payload)

    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert "phone" in data["message"].lower() or "already" in data["message"].lower()


def test_signup_duplicate_email_returns_conflict(client):
    email = f"duplicate-{uuid.uuid4().hex}@example.com"
    first_payload = {
        "full_name": "First User",
        "email": email,
        "phone": "5550000002",
        "password": "password123",
        "role": "CUSTOMER"
    }

    first_response = client.post("/auth/signup", json=first_payload)
    assert first_response.status_code == 200

    duplicate_payload = {
        "full_name": "Second User",
        "email": email,
        "phone": "5550000003",
        "password": "password123",
        "role": "CUSTOMER"
    }

    response = client.post("/auth/signup", json=duplicate_payload)

    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert "email" in data["message"].lower() or "already" in data["message"].lower()


def test_login_returns_access_token(client):
    signup_payload = {
        "full_name": "Login User",
        "email": f"login-{uuid.uuid4().hex}@example.com",
        "phone": "5550000004",
        "password": "password123",
        "role": "CUSTOMER"
    }

    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 200

    login_payload = {
        "email": signup_payload["email"],
        "password": signup_payload["password"]
    }

    response = client.post("/auth/login", json=login_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


def test_login_with_invalid_password_returns_401(client):
    signup_payload = {
        "full_name": "Login User",
        "email": f"bad-pass-{uuid.uuid4().hex}@example.com",
        "phone": "5550000005",
        "password": "password123",
        "role": "CUSTOMER"
    }

    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 200

    login_payload = {
        "email": signup_payload["email"],
        "password": "wrongpassword"
    }

    response = client.post("/auth/login", json=login_payload)

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["data"] is None