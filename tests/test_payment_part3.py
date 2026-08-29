import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.constants import PaymentStatus
from app.models.order import Order
from app.models.payment import Payment
from app.repo.user_repo import UserRepository
from app.schemas.laundry_item_type import LaundryItemTypeCreateRequest
from app.schemas.service_pricing import ServicePricingCreateRequest
from app.services.laundry_item_type_service import LaundryItemTypeService
from app.services.razorpay_service import RazorpayService
from app.services.service_pricing_service import ServicePricingService
from tests.conftest import TestingSessionLocal


# ---------- Fake Razorpay provider (duplicated from test_payment_checkout.py
# per this project's per-file test-helper convention) ----------


class FakeRazorpayProvider:
    def __init__(self):
        self.created_orders = []
        self.fetch_payment_status = "captured"
        self.payment_signature_valid = True
        self.webhook_signature_valid = True

    def create_order(self, *, amount, currency, receipt):
        order_id = f"order_fake_{uuid.uuid4().hex[:12]}"
        record = {"id": order_id, "amount": amount, "currency": currency, "receipt": receipt}
        self.created_orders.append(record)
        return record

    def fetch_payment(self, *, payment_id):
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


# ---------- Local test helpers ----------


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


PRICE = "12.50"
QUANTITY = 3


def _create_service_pricing(service_type_id, laundry_item_type_id, price=PRICE):
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


def _order_payload(address_id, service_type_id, laundry_item_type_id, payment_method="RAZORPAY", **overrides):
    payload = {
        "address_id": address_id,
        "pickup_date": "2026-08-20",
        "pickup_slot": "10:00-12:00",
        "payment_method": payment_method,
        "items": [
            {
                "laundry_item_type_id": laundry_item_type_id,
                "quantity": QUANTITY,
                "service_type_id": service_type_id,
            }
        ],
    }
    payload.update(overrides)
    return payload


def _set_status(client, order_id, status, headers):
    return client.patch(
        f"/orders/{order_id}/status",
        json={"status": status},
        headers=headers,
    )


def _get_payment_from_db(order_id: str) -> Payment:
    db = TestingSessionLocal()
    try:
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        assert order is not None and order.payment is not None
        return order.payment
    finally:
        db.close()


def _payment_count_for_order(order_id: str) -> int:
    db = TestingSessionLocal()
    try:
        return db.query(Payment).filter(Payment.order_id == uuid.UUID(order_id)).count()
    finally:
        db.close()


class _Scenario:
    """Bundles a fresh admin/customer/agents + one order with the given
    payment_method, and walks it through the operational pipeline."""

    def __init__(self, client, payment_method="RAZORPAY"):
        self.client = client
        self.admin_headers = _auth_headers(_signup(client, role="ADMIN"))
        self.customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
        self.agent_a_headers = _auth_headers(_signup(client, role="DELIVERY_AGENT"))
        self.agent_b_headers = _auth_headers(_signup(client, role="DELIVERY_AGENT"))
        self.staff_headers = _auth_headers(_signup(client, role="STAFF"))

        address = _create_address(client, self.customer_headers, label="Home")
        service_type = _create_service_type(client, self.admin_headers)
        item_type = _create_laundry_item_type()
        _create_service_pricing(service_type["id"], item_type["id"])

        response = client.post(
            "/orders/",
            json=_order_payload(
                address["id"], service_type["id"], item_type["id"], payment_method=payment_method
            ),
            headers=self.customer_headers,
        )
        assert response.status_code == 201
        self.order = response.json()["data"]

    def pay_with_razorpay(self, fake_razorpay, status="captured"):
        checkout = self.client.post(
            f"/payments/orders/{self.order['id']}/checkout", headers=self.customer_headers
        )
        assert checkout.status_code == 200
        razorpay_order_id = checkout.json()["data"]["razorpay_order_id"]

        fake_razorpay.fetch_payment_status = status
        return self.client.post(
            f"/payments/orders/{self.order['id']}/verify",
            json={
                "razorpay_payment_id": f"pay_{uuid.uuid4().hex[:10]}",
                "razorpay_order_id": razorpay_order_id,
                "razorpay_signature": "valid-sig",
            },
            headers=self.customer_headers,
        )

    def claim_and_pickup(self, headers=None):
        headers = headers or self.agent_a_headers
        claim = self.client.post(
            f"/delivery/orders/{self.order['id']}/pickup/claim", headers=headers
        )
        assert claim.status_code == 200
        return _set_status(self.client, self.order["id"], "PICKED_UP", headers)

    def advance_to_out_for_delivery(self, pickup_headers=None):
        pickup_headers = pickup_headers or self.agent_a_headers
        response = self.claim_and_pickup(pickup_headers)
        assert response.status_code == 200

        assert (
            _set_status(self.client, self.order["id"], "RECEIVED", self.staff_headers).status_code
            == 200
        )
        response = _set_status(self.client, self.order["id"], "OUT_FOR_DELIVERY", self.staff_headers)
        assert response.status_code == 200

    def claim_delivery(self, headers=None):
        headers = headers or self.agent_b_headers
        response = self.client.post(
            f"/delivery/orders/{self.order['id']}/delivery/claim", headers=headers
        )
        assert response.status_code == 200
        return headers


# ---------- Order creation ----------


def test_razorpay_order_creates_payment(client):
    scenario = _Scenario(client, payment_method="RAZORPAY")
    payment = scenario.order["payment"]

    assert payment["payment_method"] == "RAZORPAY"
    assert payment["payment_status"] == "PENDING"
    assert payment["currency"] == "INR"
    assert Decimal(payment["amount"]) == Decimal(scenario.order["total_price"])


def test_cod_order_creates_payment(client):
    scenario = _Scenario(client, payment_method="COD")
    payment = scenario.order["payment"]

    assert payment["payment_method"] == "COD"
    assert payment["payment_status"] == "PENDING"
    assert payment["currency"] == "INR"
    assert Decimal(payment["amount"]) == Decimal(scenario.order["total_price"])


def test_frontend_cannot_control_payment_amount_or_status(client):
    admin_headers = _auth_headers(_signup(client, role="ADMIN"))
    customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
    address = _create_address(client, customer_headers)
    service_type = _create_service_type(client, admin_headers)
    item_type = _create_laundry_item_type()
    _create_service_pricing(service_type["id"], item_type["id"], price=PRICE)

    payload = _order_payload(address["id"], service_type["id"], item_type["id"], payment_method="COD")
    # Extra fields a hostile client might try to slip in — schema doesn't
    # define them, so they're silently ignored, not honored.
    payload["amount"] = 1
    payload["payment_status"] = "PAID"
    payload["razorpay_order_id"] = "order_hacked"

    response = client.post("/orders/", json=payload, headers=customer_headers)
    assert response.status_code == 201

    payment = response.json()["data"]["payment"]
    expected_total = Decimal(PRICE) * QUANTITY
    assert Decimal(payment["amount"]) == expected_total
    assert payment["payment_status"] == "PENDING"


def test_exactly_one_payment_exists_per_order(client):
    scenario = _Scenario(client, payment_method="COD")
    assert _payment_count_for_order(scenario.order["id"]) == 1


# ---------- Razorpay fulfillment gate ----------


def test_unpaid_razorpay_order_cannot_enter_fulfillment(client, fake_razorpay):
    scenario = _Scenario(client, payment_method="RAZORPAY")

    response = scenario.claim_and_pickup()

    assert response.status_code == 409
    order = client.get(f"/orders/{scenario.order['id']}", headers=scenario.customer_headers).json()
    assert order["status"] == "PENDING_PICKUP"


def test_paid_razorpay_order_can_enter_fulfillment(client, fake_razorpay):
    scenario = _Scenario(client, payment_method="RAZORPAY")

    verify = scenario.pay_with_razorpay(fake_razorpay, status="captured")
    assert verify.json()["data"]["payment_status"] == "PAID"

    response = scenario.claim_and_pickup()
    assert response.status_code == 200
    assert response.json()["status"] == "PICKED_UP"


def test_failed_razorpay_payment_can_retry_and_then_enter_fulfillment(client, fake_razorpay):
    scenario = _Scenario(client, payment_method="RAZORPAY")

    scenario.pay_with_razorpay(fake_razorpay, status="failed")
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.FAILED

    retry = scenario.pay_with_razorpay(fake_razorpay, status="captured")
    assert retry.json()["data"]["payment_status"] == "PAID"

    response = scenario.claim_and_pickup()
    assert response.status_code == 200


def test_already_paid_razorpay_order_rejects_another_checkout(client, fake_razorpay):
    scenario = _Scenario(client, payment_method="RAZORPAY")
    scenario.pay_with_razorpay(fake_razorpay, status="captured")

    response = client.post(
        f"/payments/orders/{scenario.order['id']}/checkout", headers=scenario.customer_headers
    )
    assert response.status_code == 409
    assert len(fake_razorpay.created_orders) == 1


# ---------- COD ----------


def test_cod_order_can_enter_pickup_without_payment(client):
    scenario = _Scenario(client, payment_method="COD")

    response = scenario.claim_and_pickup()

    assert response.status_code == 200
    assert response.json()["status"] == "PICKED_UP"


def test_cod_payment_starts_pending(client):
    scenario = _Scenario(client, payment_method="COD")
    assert scenario.order["payment"]["payment_status"] == "PENDING"


def test_assigned_agent_can_collect_cod(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()
    scenario.claim_delivery(scenario.agent_b_headers)

    response = client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=scenario.agent_b_headers
    )

    assert response.status_code == 200
    assert response.json()["data"]["payment_status"] == "PAID"
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.PAID


def test_wrong_delivery_agent_cannot_collect_cod(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()
    scenario.claim_delivery(scenario.agent_b_headers)

    response = client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=scenario.agent_a_headers
    )

    assert response.status_code == 403
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.PENDING


def test_customer_cannot_collect_cod(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()

    response = client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=scenario.customer_headers
    )
    assert response.status_code == 403


def test_staff_cannot_normally_collect_cod(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()

    response = client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=scenario.staff_headers
    )
    assert response.status_code == 403


def test_admin_can_collect_cod_as_operational_override(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()
    scenario.claim_delivery(scenario.agent_b_headers)

    response = client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=scenario.admin_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["payment_status"] == "PAID"


def test_duplicate_cod_collection_is_idempotent(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()
    scenario.claim_delivery(scenario.agent_b_headers)
    url = f"/payments/orders/{scenario.order['id']}/cod/collect"

    first = client.post(url, headers=scenario.agent_b_headers)
    second = client.post(url, headers=scenario.agent_b_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["payment_status"] == "PAID"


def test_cod_cannot_be_collected_before_out_for_delivery(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.claim_and_pickup()

    # A DELIVERY_AGENT can never legitimately be assigned before
    # OUT_FOR_DELIVERY (claim_delivery itself requires that status), so the
    # only way to isolate this check from the ownership check is via ADMIN,
    # which bypasses ownership entirely.
    response = client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=scenario.admin_headers
    )
    assert response.status_code == 409


def test_cod_unpaid_order_cannot_become_delivered(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()
    scenario.claim_delivery(scenario.agent_b_headers)

    response = _set_status(client, scenario.order["id"], "DELIVERED", scenario.agent_b_headers)
    assert response.status_code == 409


def test_cod_paid_order_can_become_delivered(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()
    scenario.claim_delivery(scenario.agent_b_headers)
    client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=scenario.agent_b_headers
    )

    response = _set_status(client, scenario.order["id"], "DELIVERED", scenario.agent_b_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "DELIVERED"


def test_concurrent_cod_collection_is_safe(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()
    scenario.claim_delivery(scenario.agent_b_headers)
    url = f"/payments/orders/{scenario.order['id']}/cod/collect"

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(client.post, url, headers=scenario.agent_b_headers)
        future_b = executor.submit(client.post, url, headers=scenario.agent_b_headers)
        results = [future_a.result(), future_b.result()]

    assert all(r.status_code == 200 for r in results)
    assert all(r.json()["data"]["payment_status"] == "PAID" for r in results)
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.PAID


# ---------- Cancellation ----------


def test_cod_pending_cancellation_leaves_payment_pending(client):
    scenario = _Scenario(client, payment_method="COD")

    response = _set_status(client, scenario.order["id"], "CANCELLED", scenario.customer_headers)

    assert response.status_code == 200
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.PENDING


def test_razorpay_pending_cancellation_leaves_payment_pending(client, fake_razorpay):
    scenario = _Scenario(client, payment_method="RAZORPAY")

    response = _set_status(client, scenario.order["id"], "CANCELLED", scenario.customer_headers)

    assert response.status_code == 200
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.PENDING


def test_razorpay_paid_cancellation_does_not_auto_refund(client, fake_razorpay):
    scenario = _Scenario(client, payment_method="RAZORPAY")
    scenario.pay_with_razorpay(fake_razorpay, status="captured")

    response = _set_status(client, scenario.order["id"], "CANCELLED", scenario.customer_headers)

    assert response.status_code == 200
    # Cancellation never implies a refund in V1 — status stays PAID, not REFUNDED.
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.PAID


# ---------- Security ----------


def test_razorpay_secrets_never_appear_in_order_response(client, fake_razorpay):
    scenario = _Scenario(client, payment_method="RAZORPAY")
    scenario.pay_with_razorpay(fake_razorpay, status="captured")

    body = client.get(f"/orders/{scenario.order['id']}", headers=scenario.customer_headers).json()

    # payment_method legitimately equals "RAZORPAY" — the exact key set
    # already proves no razorpay_order_id/razorpay_key_secret/etc. leaked.
    assert set(body["payment"].keys()) == {"payment_method", "payment_status", "amount", "currency"}


def test_other_customer_cannot_collect_cod_on_someone_elses_order(client):
    scenario = _Scenario(client, payment_method="COD")
    scenario.advance_to_out_for_delivery()

    other_customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))

    response = client.post(
        f"/payments/orders/{scenario.order['id']}/cod/collect", headers=other_customer_headers
    )
    # Blocked at the role-check level before any order/payment ownership is
    # even considered — a customer is never in scope for COD collection.
    assert response.status_code == 403
    assert _get_payment_from_db(scenario.order["id"]).payment_status == PaymentStatus.PENDING
