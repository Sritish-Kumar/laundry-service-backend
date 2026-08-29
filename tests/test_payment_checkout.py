import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.constants import PaymentMethod, PaymentStatus
from app.models.order import Order
from app.models.payment import Payment
from app.repo.user_repo import UserRepository
from app.schemas.laundry_item_type import LaundryItemTypeCreateRequest
from app.schemas.service_pricing import ServicePricingCreateRequest
from app.services.laundry_item_type_service import LaundryItemTypeService
from app.services.razorpay_service import RazorpayService
from app.services.service_pricing_service import ServicePricingService
from tests.conftest import TestingSessionLocal


# ---------- Fake Razorpay provider ----------
# RazorpayService.provider is swapped for this in every test (via the
# `fake_razorpay` fixture) so no real network call is ever made. It gives
# each test direct control over signature validity and the provider's
# reported payment status.


class FakeRazorpayProvider:
    def __init__(self):
        self.created_orders = []
        self.fetch_payment_status = "captured"
        self.payment_signature_valid = True
        self.webhook_signature_valid = True
        self.raise_on_create_order = False
        self.raise_on_fetch_payment = False

    def create_order(self, *, amount, currency, receipt):
        if self.raise_on_create_order:
            raise RuntimeError("Razorpay API unavailable")

        order_id = f"order_fake_{uuid.uuid4().hex[:12]}"
        record = {"id": order_id, "amount": amount, "currency": currency, "receipt": receipt}
        self.created_orders.append(record)
        return record

    def fetch_payment(self, *, payment_id):
        if self.raise_on_fetch_payment:
            raise RuntimeError("Razorpay API unavailable")

        return {"id": payment_id, "status": self.fetch_payment_status}

    def verify_payment_signature(self, *, params):
        return self.payment_signature_valid

    def verify_webhook_signature(self, *, payload, signature):
        return self.webhook_signature_valid


@pytest.fixture
def fake_razorpay(monkeypatch):
    fake = FakeRazorpayProvider()
    monkeypatch.setattr(RazorpayService, "provider", fake)
    return fake


# ---------- Local test helpers (duplicated per-file, per project convention) ----------


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


def _create_order(client, headers=None):
    admin_token = _signup(client, role="ADMIN")
    customer_token = _signup(client, role="CUSTOMER")
    customer_headers = headers or _auth_headers(customer_token)

    address = _create_address(client, customer_headers, label="Home")
    service_type = _create_service_type(client, _auth_headers(admin_token))
    item_type = _create_laundry_item_type()
    _create_service_pricing(service_type["id"], item_type["id"])

    response = client.post(
        "/orders/",
        json=_order_payload(address["id"], service_type["id"], item_type["id"]),
        headers=customer_headers,
    )
    assert response.status_code == 201
    return response.json()["data"], customer_headers


def _get_payment_from_db(order_id: str) -> Payment:
    db = TestingSessionLocal()
    try:
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        assert order is not None and order.payment is not None
        return order.payment
    finally:
        db.close()


def _set_payment_fields(order_id: str, **fields) -> None:
    db = TestingSessionLocal()
    try:
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        assert order is not None and order.payment is not None
        for field, value in fields.items():
            setattr(order.payment, field, value)
        db.commit()
    finally:
        db.close()


def _webhook_payload(event: str, razorpay_order_id: str, razorpay_payment_id: str, status: str):
    return {
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": razorpay_payment_id,
                    "order_id": razorpay_order_id,
                    "status": status,
                }
            }
        },
    }


# ---------- Checkout ----------


def test_customer_can_start_checkout(client, fake_razorpay):
    order_data, headers = _create_order(client)

    response = client.post(f"/payments/orders/{order_data['id']}/checkout", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["razorpay_order_id"].startswith("order_fake_")
    assert data["currency"] == "INR"
    assert data["amount"] == RazorpayService.to_smallest_currency_unit(Decimal(order_data["total_price"]))
    assert len(fake_razorpay.created_orders) == 1
    assert fake_razorpay.created_orders[0]["receipt"] == order_data["public_order_number"]

    payment = _get_payment_from_db(order_data["id"])
    assert payment.razorpay_order_id == data["razorpay_order_id"]
    assert payment.payment_status == PaymentStatus.PENDING


def test_checkout_amount_is_computed_by_backend(client, fake_razorpay):
    order_data, headers = _create_order(client)

    client.post(f"/payments/orders/{order_data['id']}/checkout", headers=headers)

    # The checkout endpoint takes no request body at all — there is no
    # channel for the frontend to influence the amount sent to Razorpay.
    assert fake_razorpay.created_orders[0]["amount"] == RazorpayService.to_smallest_currency_unit(
        Decimal(order_data["total_price"])
    )


def test_customer_can_only_checkout_own_order(client, fake_razorpay):
    order_data, _headers = _create_order(client)

    other_customer_token = _signup(client, role="CUSTOMER")
    other_headers = _auth_headers(other_customer_token)

    response = client.post(f"/payments/orders/{order_data['id']}/checkout", headers=other_headers)

    assert response.status_code == 404
    assert len(fake_razorpay.created_orders) == 0


def test_cod_order_cannot_start_checkout(client, fake_razorpay):
    order_data, headers = _create_order(client)
    _set_payment_fields(order_data["id"], payment_method=PaymentMethod.COD)

    response = client.post(f"/payments/orders/{order_data['id']}/checkout", headers=headers)

    assert response.status_code == 409
    assert len(fake_razorpay.created_orders) == 0


def test_already_paid_order_cannot_checkout_again(client, fake_razorpay):
    order_data, headers = _create_order(client)
    _set_payment_fields(order_data["id"], payment_status=PaymentStatus.PAID)

    response = client.post(f"/payments/orders/{order_data['id']}/checkout", headers=headers)

    assert response.status_code == 409
    assert len(fake_razorpay.created_orders) == 0


def test_checkout_response_never_exposes_secrets(client, fake_razorpay):
    order_data, headers = _create_order(client)

    response = client.post(f"/payments/orders/{order_data['id']}/checkout", headers=headers)
    data = response.json()["data"]

    assert set(data.keys()) == {"razorpay_key_id", "razorpay_order_id", "amount", "currency"}
    assert "razorpay_key_secret" not in str(response.json()).lower().replace("_", "")


def test_razorpay_unavailable_does_not_mark_paid_or_change_payment(client, fake_razorpay):
    order_data, headers = _create_order(client)
    fake_razorpay.raise_on_create_order = True

    response = client.post(f"/payments/orders/{order_data['id']}/checkout", headers=headers)

    assert response.status_code == 409
    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PENDING
    assert payment.razorpay_order_id is None


# ---------- Verification ----------


def _checkout(client, order_data, headers):
    response = client.post(f"/payments/orders/{order_data['id']}/checkout", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]


def test_valid_signature_and_captured_payment_marks_paid(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    fake_razorpay.fetch_payment_status = "captured"

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["payment_status"] == "PAID"

    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PAID
    assert payment.razorpay_payment_id == "pay_ABC"


def test_invalid_signature_is_rejected_and_payment_stays_pending(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    fake_razorpay.payment_signature_valid = False

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "tampered-sig",
        },
        headers=headers,
    )

    assert response.status_code == 400
    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PENDING


def test_wrong_razorpay_order_id_is_rejected(client, fake_razorpay):
    order_data, headers = _create_order(client)
    _checkout(client, order_data, headers)

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": "order_someone_elses",
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )

    assert response.status_code == 400
    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PENDING


def test_wrong_payment_id_fails_signature_check(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    # A signature generated for a different payment_id will not verify
    # against the one actually submitted.
    fake_razorpay.payment_signature_valid = False

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_NOT_THE_REAL_ONE",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "sig-for-a-different-payment",
        },
        headers=headers,
    )

    assert response.status_code == 400


def test_payment_becomes_paid_only_after_verification(client, fake_razorpay):
    order_data, headers = _create_order(client)
    _checkout(client, order_data, headers)

    assert _get_payment_from_db(order_data["id"]).payment_status == PaymentStatus.PENDING

    order_response = client.get(f"/orders/{order_data['id']}", headers=headers)
    assert order_response.json()["payment"]["payment_status"] == "PENDING"


def test_verify_leaves_payment_pending_when_not_yet_captured(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    fake_razorpay.fetch_payment_status = "authorized"

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["payment_status"] == "PENDING"


def test_verify_marks_failed_when_provider_reports_failed(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    fake_razorpay.fetch_payment_status = "failed"

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["payment_status"] == "FAILED"


def test_verify_is_idempotent_once_already_paid(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    first = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )
    assert first.json()["data"]["payment_status"] == "PAID"

    # Even a bogus signature on a second call must not error or change
    # anything — the payment is already settled.
    fake_razorpay.payment_signature_valid = False
    second = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "whatever",
        },
        headers=headers,
    )

    assert second.status_code == 200
    assert second.json()["data"]["payment_status"] == "PAID"


def test_fetch_payment_failure_does_not_mark_paid(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    fake_razorpay.raise_on_fetch_payment = True

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert _get_payment_from_db(order_data["id"]).payment_status == PaymentStatus.PENDING


def test_customer_cannot_verify_another_customers_payment(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    other_customer_token = _signup(client, role="CUSTOMER")
    other_headers = _auth_headers(other_customer_token)

    response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_ABC",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=other_headers,
    )

    assert response.status_code == 404


# ---------- Webhook ----------


def test_valid_webhook_marks_payment_paid(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    response = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.captured", checkout["razorpay_order_id"], "pay_WH1", "captured"),
        headers={"X-Razorpay-Signature": "valid-webhook-sig"},
    )

    assert response.status_code == 200
    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PAID
    assert payment.razorpay_payment_id == "pay_WH1"


def test_invalid_webhook_signature_is_rejected(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    fake_razorpay.webhook_signature_valid = False

    response = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.captured", checkout["razorpay_order_id"], "pay_WH1", "captured"),
        headers={"X-Razorpay-Signature": "tampered"},
    )

    assert response.status_code == 400
    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PENDING


def test_webhook_missing_signature_header_is_rejected(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    response = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.captured", checkout["razorpay_order_id"], "pay_WH1", "captured"),
    )

    assert response.status_code == 400


def test_webhook_requires_no_jwt(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    # No Authorization header at all — only the Razorpay signature header.
    response = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.captured", checkout["razorpay_order_id"], "pay_WH1", "captured"),
        headers={"X-Razorpay-Signature": "valid-webhook-sig"},
    )

    assert response.status_code == 200


def test_payment_failed_webhook_marks_payment_failed(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    response = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.failed", checkout["razorpay_order_id"], "pay_WH2", "failed"),
        headers={"X-Razorpay-Signature": "valid-webhook-sig"},
    )

    assert response.status_code == 200
    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.FAILED


def test_duplicate_webhook_delivery_is_safe(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    payload = _webhook_payload("payment.captured", checkout["razorpay_order_id"], "pay_WH1", "captured")
    headers_wh = {"X-Razorpay-Signature": "valid-webhook-sig"}

    first = client.post("/payments/webhooks/razorpay", json=payload, headers=headers_wh)
    second = client.post("/payments/webhooks/razorpay", json=payload, headers=headers_wh)

    assert first.status_code == 200
    assert second.status_code == 200
    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PAID
    assert payment.razorpay_payment_id == "pay_WH1"


def test_captured_webhook_rescues_a_payment_that_previously_failed(client, fake_razorpay):
    # Razorpay lets a customer retry within the same order_id after a
    # failed attempt — a later successful attempt must still win, even
    # though an earlier webhook already flipped the payment to FAILED.
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)
    headers_wh = {"X-Razorpay-Signature": "valid-webhook-sig"}

    first_attempt = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.failed", checkout["razorpay_order_id"], "pay_ATTEMPT1", "failed"),
        headers=headers_wh,
    )
    assert first_attempt.status_code == 200
    assert _get_payment_from_db(order_data["id"]).payment_status == PaymentStatus.FAILED

    second_attempt = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.captured", checkout["razorpay_order_id"], "pay_ATTEMPT2", "captured"),
        headers=headers_wh,
    )
    assert second_attempt.status_code == 200

    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PAID
    assert payment.razorpay_payment_id == "pay_ATTEMPT2"


def test_webhook_before_callback_then_callback_is_safe(client, fake_razorpay):
    order_data, headers = _create_order(client)
    checkout = _checkout(client, order_data, headers)

    webhook_response = client.post(
        "/payments/webhooks/razorpay",
        json=_webhook_payload("payment.captured", checkout["razorpay_order_id"], "pay_WH1", "captured"),
        headers={"X-Razorpay-Signature": "valid-webhook-sig"},
    )
    assert webhook_response.status_code == 200
    assert _get_payment_from_db(order_data["id"]).payment_status == PaymentStatus.PAID

    # Browser callback arrives afterwards — must be a safe idempotent no-op,
    # even with a signature that would otherwise be considered invalid.
    fake_razorpay.payment_signature_valid = False
    callback_response = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_WH1",
            "razorpay_order_id": checkout["razorpay_order_id"],
            "razorpay_signature": "irrelevant",
        },
        headers=headers,
    )

    assert callback_response.status_code == 200
    assert callback_response.json()["data"]["payment_status"] == "PAID"


# ---------- Retry ----------


def test_failed_payment_can_be_retried_with_a_fresh_razorpay_order(client, fake_razorpay):
    order_data, headers = _create_order(client)
    first_checkout = _checkout(client, order_data, headers)

    fake_razorpay.fetch_payment_status = "failed"
    client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_FAIL1",
            "razorpay_order_id": first_checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )
    assert _get_payment_from_db(order_data["id"]).payment_status == PaymentStatus.FAILED

    second_checkout = _checkout(client, order_data, headers)
    assert second_checkout["razorpay_order_id"] != first_checkout["razorpay_order_id"]
    assert _get_payment_from_db(order_data["id"]).payment_status == PaymentStatus.PENDING

    fake_razorpay.fetch_payment_status = "captured"
    retry_verify = client.post(
        f"/payments/orders/{order_data['id']}/verify",
        json={
            "razorpay_payment_id": "pay_RETRY1",
            "razorpay_order_id": second_checkout["razorpay_order_id"],
            "razorpay_signature": "valid-sig",
        },
        headers=headers,
    )

    assert retry_verify.status_code == 200
    assert retry_verify.json()["data"]["payment_status"] == "PAID"

    payment = _get_payment_from_db(order_data["id"])
    assert payment.payment_status == PaymentStatus.PAID
    assert payment.razorpay_order_id == second_checkout["razorpay_order_id"]
    assert payment.razorpay_payment_id == "pay_RETRY1"
