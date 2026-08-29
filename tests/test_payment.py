import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.constants import PaymentMethod, PaymentStatus
from app.models.order import Order
from app.models.payment import Payment
from app.repo.payment_repo import PaymentRepository
from app.repo.user_repo import UserRepository
from app.schemas.payment import PaymentResponse
from app.services.razorpay_service import RazorpayService
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


def _create_customer_user_id(client) -> uuid.UUID:
    """Signs a customer up through the real API (so auth invariants like
    email verification hold) and returns their user id, for use as the FK
    on a bare Order below."""
    payload = _signup_payload()
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    _mark_user_verified(payload["email"])

    db = TestingSessionLocal()
    try:
        user = UserRepository.get_user_by_email(db, payload["email"])
        assert user is not None
        return user.id
    finally:
        db.close()


def _create_bare_order(user_id: uuid.UUID, total_price: str = "57.50") -> dict:
    """Inserts an Order directly, bypassing OrderService entirely — Part 2
    made OrderService.create_order also create a Payment, but these tests
    are specifically about the Payment model/repo layer in isolation."""
    db = TestingSessionLocal()
    try:
        order = Order(
            public_order_number=f"ORD-TEST-{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            pickup_date=date(2026, 8, 20),
            pickup_slot="10:00-12:00",
            total_price=Decimal(total_price),
            recipient_name="Jane Doe",
            recipient_phone="5551234567",
            address_line_1="123 Main St",
            address_line_2=None,
            landmark=None,
            city="Springfield",
            state="IL",
            postal_code="62704",
            country="USA",
            latitude=Decimal("39.781721"),
            longitude=Decimal("-89.650148"),
            location_accuracy=None,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return {"id": order.id, "total_price": order.total_price}
    finally:
        db.close()


def _create_order(client) -> dict:
    user_id = _create_customer_user_id(client)
    return _create_bare_order(user_id)


# ---------- Model / relationship tests ----------


def test_payment_belongs_to_exactly_one_order(client):
    order_data = _create_order(client)

    db = TestingSessionLocal()
    try:
        payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.COD,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
        )
        created = PaymentRepository.create(db, payment)

        assert created.order_id == order_data["id"]
        assert created.order.id == order_data["id"]
    finally:
        db.close()


def test_order_payment_relationship_both_directions(client):
    order_data = _create_order(client)

    db = TestingSessionLocal()
    try:
        payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
        )
        PaymentRepository.create(db, payment)

        order = db.query(Order).filter(Order.id == order_data["id"]).first()
        assert order is not None
        assert order.payment is not None
        assert order.payment.id == payment.id
        assert payment.order.id == order.id
    finally:
        db.close()


def test_order_can_have_at_most_one_payment(client):
    order_data = _create_order(client)

    db = TestingSessionLocal()
    try:
        first_payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.COD,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
        )
        PaymentRepository.create(db, first_payment)
    finally:
        db.close()

    db = TestingSessionLocal()
    try:
        second_payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
        )
        db.add(second_payment)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_payment_amount_and_currency_stored_correctly(client):
    order_data = _create_order(client)

    db = TestingSessionLocal()
    try:
        payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
        )
        created = PaymentRepository.create(db, payment)

        assert created.amount == order_data["total_price"]
        assert created.currency == "INR"
    finally:
        db.close()


def test_razorpay_ids_are_nullable_for_cod(client):
    order_data = _create_order(client)

    db = TestingSessionLocal()
    try:
        payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.COD,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
        )
        created = PaymentRepository.create(db, payment)

        assert created.razorpay_order_id is None
        assert created.razorpay_payment_id is None
    finally:
        db.close()


def test_payment_method_and_status_enum_values():
    assert {member.value for member in PaymentMethod} == {"RAZORPAY", "COD"}
    assert {member.value for member in PaymentStatus} == {
        "PENDING",
        "PAID",
        "FAILED",
        "REFUNDED",
    }


def test_payment_repo_lookup_and_update(client):
    order_data = _create_order(client)

    db = TestingSessionLocal()
    try:
        payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
            razorpay_order_id="order_test123",
        )
        created = PaymentRepository.create(db, payment)

        by_id = PaymentRepository.get_by_id(db, created.id)
        assert by_id is not None and by_id.id == created.id

        by_order_id = PaymentRepository.get_by_order_id(db, created.order_id)
        assert by_order_id is not None and by_order_id.id == created.id

        by_razorpay_order_id = PaymentRepository.get_by_razorpay_order_id(db, "order_test123")
        assert by_razorpay_order_id is not None and by_razorpay_order_id.id == created.id

        updated = PaymentRepository.update(db, created, {"payment_status": PaymentStatus.PAID})
        assert updated.payment_status == PaymentStatus.PAID
    finally:
        db.close()


# ---------- Configuration / Razorpay service tests ----------


def test_razorpay_config_loads_from_settings():
    assert hasattr(settings, "RAZORPAY_KEY_ID")
    assert hasattr(settings, "RAZORPAY_KEY_SECRET")
    assert hasattr(settings, "RAZORPAY_WEBHOOK_SECRET")


def test_razorpay_service_initializes_with_a_provider():
    assert RazorpayService.provider is not None


def test_razorpay_amount_conversion_to_smallest_unit():
    assert RazorpayService.to_smallest_currency_unit(Decimal("500")) == 50000
    assert RazorpayService.to_smallest_currency_unit(Decimal("37.50")) == 3750


# ---------- Schema tests ----------


def test_payment_response_schema_excludes_provider_secrets(client):
    order_data = _create_order(client)

    db = TestingSessionLocal()
    try:
        payment = Payment(
            order_id=order_data["id"],
            payment_method=PaymentMethod.COD,
            payment_status=PaymentStatus.PENDING,
            amount=order_data["total_price"],
        )
        created = PaymentRepository.create(db, payment)

        dumped = PaymentResponse.model_validate(created).model_dump()

        assert dumped == {
            "payment_method": "COD",
            "payment_status": "PENDING",
            "amount": order_data["total_price"],
            "currency": "INR",
        }
    finally:
        db.close()
