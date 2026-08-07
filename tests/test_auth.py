import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.constants import UserRole, VerificationPurpose
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.repo.auth_session_repo import AuthSessionRepository
from app.repo.user_repo import UserRepository
from app.services.email_service import EmailService
from tests.conftest import TestingSessionLocal


def _signup_payload(**overrides):
    unique_id = uuid.uuid4().hex
    phone_suffix = uuid.uuid4().int % 10000000
    payload = {
        "full_name": "Refresh User",
        "email": f"refresh-{unique_id}@example.com",
        "phone": f"555{phone_suffix:07d}",
        "password": "password123",
        "role": "CUSTOMER"
    }
    payload.update(overrides)
    return payload


def _signup(client, **overrides):
    payload = _signup_payload(**overrides)
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201

    _mark_user_verified(payload["email"])

    login_response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    return login_response.json()["data"]


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


def _assert_unauthorized(response):
    assert response.status_code == 401
    data = response.json()
    if "success" in data:
        assert data["success"] is False
        assert data["data"] is None


def test_send_verification_email_renders_template_placeholders(monkeypatch):
    captured = {}

    class FakeProvider:
        def send(self, *, email_message):
            captured["html"] = email_message.html

    monkeypatch.setattr(EmailService, "provider", FakeProvider())

    EmailService.send_verification_email(
        recipient="user@example.com",
        purpose=VerificationPurpose.EMAIL_VERIFICATION,
        otp="123456",
    )

    assert "123456" in captured["html"]
    assert "{{ otp }}" not in captured["html"]
    assert "{{ expiry_minutes }}" not in captured["html"]


def _as_utc_datetime(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


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

    if response.status_code != 201:
        print("ERROR RESPONSE:", response.json())

    assert response.status_code == 201

    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert data["data"]["email"] == payload["email"]
    assert data["data"]["message"] == "Verification code sent successfully."


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
    assert first_response.status_code == 201

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
    assert first_response.status_code == 201
    _mark_user_verified(first_payload["email"])

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
    assert signup_response.status_code == 201
    _mark_user_verified(signup_payload["email"])

    login_payload = {
        "email": signup_payload["email"],
        "password": signup_payload["password"]
    }

    response = client.post("/auth/login", json=login_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert data["data"]["token_type"] == "bearer"


def test_token_endpoint_returns_oauth2_token_shape(client):
    signup_payload = {
        "full_name": "Swagger User",
        "email": f"swagger-{uuid.uuid4().hex}@example.com",
        "phone": "5550000040",
        "password": "password123",
        "role": "CUSTOMER"
    }

    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    _mark_user_verified(signup_payload["email"])

    response = client.post(
        "/auth/token",
        data={
            "username": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert data["token_type"] == "bearer"
    assert "data" not in data


def test_login_with_invalid_password_returns_401(client):
    signup_payload = {
        "full_name": "Login User",
        "email": f"bad-pass-{uuid.uuid4().hex}@example.com",
        "phone": "5550000005",
        "password": "password123",
        "role": "CUSTOMER"
    }

    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    _mark_user_verified(signup_payload["email"])

    login_payload = {
        "email": signup_payload["email"],
        "password": "wrongpassword"
    }

    response = client.post("/auth/login", json=login_payload)

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["data"] is None


def test_login_unverified_user_returns_401_and_resends_verification(client):
    signup_payload = {
        "full_name": "Pending User",
        "email": f"pending-{uuid.uuid4().hex}@example.com",
        "phone": "5550000006",
        "password": "password123",
        "role": "CUSTOMER"
    }

    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["data"] is None
    assert data["message"] == "Your email is not verified. A new verification code has been sent."


def test_resend_verification_returns_generic_success_for_unknown_email(client):
    response = client.post(
        "/auth/resend-verification",
        json={"email": f"unknown-{uuid.uuid4().hex}@example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "If an account exists and requires verification, a verification code has been sent."
    assert data["data"] is None


def test_forgot_password_returns_generic_success_and_allows_reset(client, db_session, monkeypatch):
    payload = {
        "full_name": "Reset User",
        "email": f"forgot-{uuid.uuid4().hex}@example.com",
        "phone": "5550000007",
        "password": "password123",
        "role": "CUSTOMER",
    }

    signup_response = client.post("/auth/signup", json=payload)
    assert signup_response.status_code == 201
    _mark_user_verified(payload["email"])

    monkeypatch.setattr("app.services.verification_service.generate_otp", lambda: "123456")

    forgot_response = client.post("/auth/forgot-password", json={"email": payload["email"]})
    assert forgot_response.status_code == 200
    assert forgot_response.json()["message"] == "If an account exists, a password reset code has been sent."

    reset_response = client.post(
        "/auth/reset-password",
        json={"email": payload["email"], "otp": "123456", "new_password": "newpassword123"},
    )

    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password reset successfully."

    user = UserRepository.get_user_by_email(db_session, payload["email"])
    assert user is not None
    assert verify_password("newpassword123", user.password_hash)

    sessions = AuthSessionRepository.get_user_sessions(db_session, user.id, active_only=False)
    assert all(session.revoked_at is not None for session in sessions)


def test_change_password_logs_out_all_sessions(client, db_session):
    payload = {
        "full_name": "Password User",
        "email": f"change-pass-{uuid.uuid4().hex}@example.com",
        "phone": "5550000010",
        "password": "password123",
        "role": "CUSTOMER",
    }
    signup_response = client.post("/auth/signup", json=payload)
    assert signup_response.status_code == 201
    _mark_user_verified(payload["email"])

    login_response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()["data"]
    refresh_token = token_data["refresh_token"]
    user = UserRepository.get_user_by_email(db_session, payload["email"])

    response = client.post(
        "/auth/change-password",
        json={"current_password": "password123", "new_password": "updatedpassword123"},
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully."

    sessions = AuthSessionRepository.get_user_sessions(db_session, user.id, active_only=False)
    assert all(session.revoked_at is not None for session in sessions)

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401


def test_change_email_sends_verification_and_confirms_new_address(client, db_session, monkeypatch):
    payload = {
        "full_name": "Email User",
        "email": f"change-email-{uuid.uuid4().hex}@example.com",
        "phone": "5550000011",
        "password": "password123",
        "role": "CUSTOMER",
    }
    signup_response = client.post("/auth/signup", json=payload)
    assert signup_response.status_code == 201
    _mark_user_verified(payload["email"])

    login_response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()["data"]
    monkeypatch.setattr("app.services.verification_service.generate_otp", lambda: "654321")

    initiate_response = client.post(
        "/auth/change-email",
        json={"new_email": "updated@example.com"},
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )

    assert initiate_response.status_code == 200
    assert initiate_response.json()["message"] == "Verification code sent to your new email address."

    confirm_response = client.post(
        "/auth/confirm-change-email",
        json={"new_email": "updated@example.com", "otp": "654321"},
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["message"] == "Email changed successfully."

    user = UserRepository.get_user_by_email(db_session, "updated@example.com")
    assert user is not None
    assert user.is_email_verified is True
    assert user.email_verified_at is not None


def test_refresh_returns_new_access_token_and_new_refresh_token(client, db_session):
    token_data = _signup(client)
    refresh_token = token_data["refresh_token"]
    auth_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(refresh_token),
    )
    assert auth_session is not None
    last_used_at = _as_utc_datetime(auth_session.last_used_at)

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["access_token"] != token_data["access_token"]
    assert data["data"]["refresh_token"] != refresh_token
    assert data["data"]["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert data["data"]["token_type"] == "bearer"

    new_refresh_token = data["data"]["refresh_token"]
    db_session.expire_all()
    db_session.refresh(auth_session)
    stored_expires_at = _as_utc_datetime(auth_session.expires_at)

    assert auth_session.refresh_token_hash == hash_refresh_token(new_refresh_token)
    assert stored_expires_at >= last_used_at + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        seconds=-1,
    )
    assert _as_utc_datetime(auth_session.last_used_at) >= last_used_at


def test_refresh_rejects_old_refresh_token_after_rotation(client):
    token_data = _signup(client)
    refresh_token = token_data["refresh_token"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    _assert_unauthorized(response)


def test_refresh_accepts_latest_refresh_token_after_rotation(client):
    token_data = _signup(client)

    first_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )
    assert first_refresh_response.status_code == 200
    first_refresh_data = first_refresh_response.json()["data"]

    second_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh_data["refresh_token"]},
    )

    assert second_refresh_response.status_code == 200
    second_refresh_data = second_refresh_response.json()["data"]
    assert first_refresh_data["access_token"] != token_data["access_token"]
    assert first_refresh_data["refresh_token"] != token_data["refresh_token"]
    assert second_refresh_data["access_token"] != first_refresh_data["access_token"]
    assert second_refresh_data["refresh_token"] != first_refresh_data["refresh_token"]


def test_refresh_with_expired_refresh_token_returns_401(client):
    expired_at = datetime.now(UTC) - timedelta(minutes=1)
    expired_refresh_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "type": "refresh",
            "jti": str(uuid.uuid4()),
            "iat": expired_at - timedelta(minutes=5),
            "exp": expired_at,
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = client.post("/auth/refresh", json={"refresh_token": expired_refresh_token})

    _assert_unauthorized(response)


def test_refresh_with_revoked_session_returns_401(client, db_session):
    token_data = _signup(client)
    auth_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(token_data["refresh_token"]),
    )
    assert auth_session is not None
    AuthSessionRepository.revoke_session(db_session, auth_session.id)

    response = client.post("/auth/refresh", json={"refresh_token": token_data["refresh_token"]})

    _assert_unauthorized(response)


def test_refresh_with_missing_session_returns_401(client):
    refresh_token = create_refresh_token(
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
    )

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    _assert_unauthorized(response)


def test_refresh_with_invalid_signature_returns_401(client):
    token_data = _signup(client)
    refresh_token = token_data["refresh_token"]
    header, payload, signature = refresh_token.split(".")
    replacement_char = "a" if signature[0] != "a" else "b"
    modified_refresh_token = f"{header}.{payload}.{replacement_char}{signature[1:]}"

    response = client.post("/auth/refresh", json={"refresh_token": modified_refresh_token})

    _assert_unauthorized(response)


def test_refresh_with_access_token_returns_401(client):
    user_id = uuid.uuid4()
    access_token = create_access_token(
        user_id=user_id,
        role=UserRole.CUSTOMER,
        session_id=uuid.uuid4(),
    )

    response = client.post("/auth/refresh", json={"refresh_token": access_token})

    _assert_unauthorized(response)


def test_logout_revokes_current_session(client, db_session):
    token_data = _signup(client)
    refresh_token = token_data["refresh_token"]

    response = client.post("/auth/logout", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"] is None

    auth_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(refresh_token),
    )
    assert auth_session is not None
    db_session.refresh(auth_session)
    assert auth_session.revoked_at is not None


def test_logout_revoked_session_cannot_refresh(client):
    token_data = _signup(client)
    refresh_token = token_data["refresh_token"]

    logout_response = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    _assert_unauthorized(response)


def test_logout_with_invalid_refresh_token_returns_401(client):
    token_data = _signup(client)
    refresh_token = token_data["refresh_token"]
    header, payload, signature = refresh_token.split(".")
    replacement_char = "a" if signature[0] != "a" else "b"
    modified_refresh_token = f"{header}.{payload}.{replacement_char}{signature[1:]}"

    response = client.post("/auth/logout", json={"refresh_token": modified_refresh_token})

    _assert_unauthorized(response)


def test_logout_only_revokes_matching_session(client):
    signup_payload = _signup_payload()
    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    _mark_user_verified(signup_payload["email"])

    laptop_login_response = client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert laptop_login_response.status_code == 200
    laptop_token_data = laptop_login_response.json()["data"]

    phone_login_response = client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert phone_login_response.status_code == 200
    phone_token_data = phone_login_response.json()["data"]

    logout_response = client.post(
        "/auth/logout",
        json={"refresh_token": laptop_token_data["refresh_token"]},
    )
    assert logout_response.status_code == 200

    laptop_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": laptop_token_data["refresh_token"]},
    )
    _assert_unauthorized(laptop_refresh_response)

    phone_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": phone_token_data["refresh_token"]},
    )
    assert phone_refresh_response.status_code == 200


def test_logout_all_revokes_all_user_sessions(client):
    signup_payload = _signup_payload()
    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    _mark_user_verified(signup_payload["email"])

    first_login_response = client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert first_login_response.status_code == 200
    first_session_data = first_login_response.json()["data"]

    second_login_response = client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert second_login_response.status_code == 200
    second_session_data = second_login_response.json()["data"]

    response = client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {first_session_data['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"] is None

    first_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": first_session_data["refresh_token"]},
    )
    _assert_unauthorized(first_refresh_response)

    second_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": second_session_data["refresh_token"]},
    )
    _assert_unauthorized(second_refresh_response)


def test_logout_all_requires_access_token(client):
    response = client.post("/auth/logout-all")

    _assert_unauthorized(response)


def test_get_sessions_marks_current_and_excludes_revoked_sessions(client, db_session):
    signup_payload = _signup_payload()
    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    _mark_user_verified(signup_payload["email"])

    first_login_response = client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert first_login_response.status_code == 200
    first_token_data = first_login_response.json()["data"]

    second_login_response = client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert second_login_response.status_code == 200
    second_token_data = second_login_response.json()["data"]

    first_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(first_token_data["refresh_token"]),
    )
    second_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(second_token_data["refresh_token"]),
    )
    assert first_session is not None
    assert second_session is not None

    AuthSessionRepository.revoke_session(db_session, second_session.id)

    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {first_token_data['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == str(first_session.id)
    assert data["data"][0]["current"] is True
    assert data["data"][0]["device_type"] == "WEB"


def test_revoke_session_requires_ownership_and_revokes_matching_session(client, db_session):
    first_token_data = _signup(client)
    second_token_data = _signup(client)

    second_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(second_token_data["refresh_token"]),
    )
    first_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(first_token_data["refresh_token"]),
    )
    assert first_session is not None
    assert second_session is not None

    cross_user_response = client.delete(
        f"/auth/sessions/{second_session.id}",
        headers={"Authorization": f"Bearer {first_token_data['access_token']}"},
    )
    assert cross_user_response.status_code == 404
    assert cross_user_response.json()["data"] is None

    revoke_response = client.delete(
        f"/auth/sessions/{first_session.id}",
        headers={"Authorization": f"Bearer {first_token_data['access_token']}"},
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["data"] is None

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": first_token_data["refresh_token"]},
    )
    _assert_unauthorized(refresh_response)

    other_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": second_token_data["refresh_token"]},
    )
    assert other_refresh_response.status_code == 200


def test_cleanup_methods_delete_expired_and_revoked_sessions(client, db_session):
    first_token_data = _signup(client)
    second_token_data = _signup(client)

    expired_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(first_token_data["refresh_token"]),
    )
    revoked_session = AuthSessionRepository.get_by_refresh_hash(
        db_session,
        hash_refresh_token(second_token_data["refresh_token"]),
    )
    assert expired_session is not None
    assert revoked_session is not None

    expired_session_id = expired_session.id
    revoked_session_id = revoked_session.id
    expired_session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    AuthSessionRepository.revoke_session(db_session, revoked_session_id)
    db_session.commit()

    assert AuthSessionRepository.cleanup_expired_sessions(db_session) == 1
    assert AuthSessionRepository.get_by_id(db_session, expired_session_id) is None
    assert AuthSessionRepository.get_by_id(db_session, revoked_session_id) is not None

    assert AuthSessionRepository.cleanup_revoked_sessions(db_session) == 1
    assert AuthSessionRepository.get_by_id(db_session, revoked_session_id) is None
