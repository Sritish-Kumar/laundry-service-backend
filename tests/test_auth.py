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