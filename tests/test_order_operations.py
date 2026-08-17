import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from app.models.order_status_history import OrderStatusHistory
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
        "current_price": "12.50",
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


def _order_payload(address_id, service_type_id, **overrides):
    payload = {
        "address_id": address_id,
        "pickup_date": "2026-08-20",
        "pickup_slot": "10:00-12:00",
        "items": [
            {"cloth_type": "Shirt", "quantity": 3, "service_type_id": service_type_id}
        ],
    }
    payload.update(overrides)
    return payload


def _create_order(client, customer_headers, address_id, service_type_id):
    response = client.post(
        "/orders/",
        json=_order_payload(address_id, service_type_id),
        headers=customer_headers,
    )
    assert response.status_code == 201
    return response.json()["data"]


def _set_status(client, order_id, status, headers):
    return client.patch(
        f"/orders/{order_id}/status",
        json={"status": status},
        headers=headers,
    )


def _status_history_count(order_id: str) -> int:
    db = TestingSessionLocal()
    try:
        return (
            db.query(OrderStatusHistory)
            .filter(OrderStatusHistory.order_id == uuid.UUID(order_id))
            .count()
        )
    finally:
        db.close()


class _Scenario:
    """Bundles a fresh admin/customer/agents + one PENDING_PICKUP order."""

    def __init__(self, client):
        self.client = client
        self.admin_headers = _auth_headers(_signup(client, role="ADMIN"))
        self.customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))
        self.agent_a_headers = _auth_headers(_signup(client, role="DELIVERY_AGENT"))
        self.agent_b_headers = _auth_headers(_signup(client, role="DELIVERY_AGENT"))
        self.staff_headers = _auth_headers(_signup(client, role="STAFF"))

        address = _create_address(client, self.customer_headers, label="Home")
        service_type = _create_service_type(client, self.admin_headers)

        self.order = _create_order(
            client, self.customer_headers, address["id"], service_type["id"]
        )

    def advance_to_out_for_delivery(self):
        """Walks the order PENDING_PICKUP -> ... -> OUT_FOR_DELIVERY via the bulk shortcut."""
        client, order_id = self.client, self.order["id"]

        claim = client.post(
            f"/delivery/orders/{order_id}/pickup/claim",
            headers=self.agent_a_headers,
        )
        assert claim.status_code == 200

        assert _set_status(client, order_id, "PICKED_UP", self.agent_a_headers).status_code == 200
        assert _set_status(client, order_id, "RECEIVED", self.staff_headers).status_code == 200
        assert (
            _set_status(client, order_id, "OUT_FOR_DELIVERY", self.staff_headers).status_code
            == 200
        )


# ---------- Pickup assignment ----------


def test_delivery_agent_sees_available_pickups(client):
    scenario = _Scenario(client)

    response = client.get("/delivery/orders/pickups", headers=scenario.agent_a_headers)

    assert response.status_code == 200
    order_ids = [o["id"] for o in response.json()]
    assert scenario.order["id"] in order_ids


def test_delivery_agent_claims_pickup(client):
    scenario = _Scenario(client)

    response = client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_a_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


def test_claim_does_not_change_status(client):
    scenario = _Scenario(client)

    client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_a_headers,
    )

    order_response = client.get(
        f"/orders/{scenario.order['id']}", headers=scenario.customer_headers
    )
    assert order_response.json()["status"] == "PENDING_PICKUP"


def test_claimed_order_disappears_from_available_pool(client):
    scenario = _Scenario(client)

    client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_a_headers,
    )

    pool = client.get("/delivery/orders/pickups", headers=scenario.agent_b_headers)
    order_ids = [o["id"] for o in pool.json()]
    assert scenario.order["id"] not in order_ids


def test_agent_sees_claimed_order_in_my_pickups(client):
    scenario = _Scenario(client)

    client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_a_headers,
    )

    mine = client.get("/delivery/orders/pickups/mine", headers=scenario.agent_a_headers)
    order_ids = [o["id"] for o in mine.json()]
    assert scenario.order["id"] in order_ids


def test_another_agent_cannot_claim_already_claimed_pickup(client):
    scenario = _Scenario(client)

    first = client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_a_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_b_headers,
    )
    assert second.status_code == 409


def test_concurrent_pickup_claim_allows_only_one_winner(client):
    scenario = _Scenario(client)
    url = f"/delivery/orders/{scenario.order['id']}/pickup/claim"

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(client.post, url, headers=scenario.agent_a_headers)
        future_b = executor.submit(client.post, url, headers=scenario.agent_b_headers)
        status_codes = sorted([future_a.result().status_code, future_b.result().status_code])

    assert status_codes == [200, 409]


# ---------- Delivery assignment ----------


def test_delivery_agent_sees_available_deliveries(client):
    scenario = _Scenario(client)
    scenario.advance_to_out_for_delivery()

    response = client.get("/delivery/orders/deliveries", headers=scenario.agent_b_headers)

    assert response.status_code == 200
    order_ids = [o["id"] for o in response.json()]
    assert scenario.order["id"] in order_ids


def test_agent_claims_delivery(client):
    scenario = _Scenario(client)
    scenario.advance_to_out_for_delivery()

    response = client.post(
        f"/delivery/orders/{scenario.order['id']}/delivery/claim",
        headers=scenario.agent_b_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_delivery_claim_does_not_change_status(client):
    scenario = _Scenario(client)
    scenario.advance_to_out_for_delivery()

    client.post(
        f"/delivery/orders/{scenario.order['id']}/delivery/claim",
        headers=scenario.agent_b_headers,
    )

    order_response = client.get(
        f"/orders/{scenario.order['id']}", headers=scenario.customer_headers
    )
    assert order_response.json()["status"] == "OUT_FOR_DELIVERY"


def test_claimed_delivery_disappears_from_pool(client):
    scenario = _Scenario(client)
    scenario.advance_to_out_for_delivery()

    client.post(
        f"/delivery/orders/{scenario.order['id']}/delivery/claim",
        headers=scenario.agent_b_headers,
    )

    pool = client.get("/delivery/orders/deliveries", headers=scenario.agent_a_headers)
    order_ids = [o["id"] for o in pool.json()]
    assert scenario.order["id"] not in order_ids


def test_agent_sees_claimed_order_in_my_deliveries(client):
    scenario = _Scenario(client)
    scenario.advance_to_out_for_delivery()

    client.post(
        f"/delivery/orders/{scenario.order['id']}/delivery/claim",
        headers=scenario.agent_b_headers,
    )

    mine = client.get("/delivery/orders/deliveries/mine", headers=scenario.agent_b_headers)
    order_ids = [o["id"] for o in mine.json()]
    assert scenario.order["id"] in order_ids


def test_another_agent_cannot_claim_already_claimed_delivery(client):
    scenario = _Scenario(client)
    scenario.advance_to_out_for_delivery()

    first = client.post(
        f"/delivery/orders/{scenario.order['id']}/delivery/claim",
        headers=scenario.agent_a_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/delivery/orders/{scenario.order['id']}/delivery/claim",
        headers=scenario.agent_b_headers,
    )
    assert second.status_code == 409


# ---------- Authorization ----------


def test_customer_cannot_claim_pickup(client):
    scenario = _Scenario(client)

    response = client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.customer_headers,
    )
    assert response.status_code == 403


def test_staff_cannot_claim_pickup(client):
    scenario = _Scenario(client)

    response = client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.staff_headers,
    )
    assert response.status_code == 403


def test_customer_cannot_perform_operational_transition(client):
    scenario = _Scenario(client)

    response = _set_status(client, scenario.order["id"], "PICKED_UP", scenario.customer_headers)
    assert response.status_code == 403


def test_unassigned_agent_cannot_mark_picked_up(client):
    scenario = _Scenario(client)

    client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_a_headers,
    )

    response = _set_status(client, scenario.order["id"], "PICKED_UP", scenario.agent_b_headers)
    assert response.status_code == 403


def test_wrong_delivery_agent_cannot_mark_delivered(client):
    scenario = _Scenario(client)
    scenario.advance_to_out_for_delivery()

    client.post(
        f"/delivery/orders/{scenario.order['id']}/delivery/claim",
        headers=scenario.agent_a_headers,
    )

    response = _set_status(client, scenario.order["id"], "DELIVERED", scenario.agent_b_headers)
    assert response.status_code == 403


def test_admin_can_perform_valid_transition(client):
    scenario = _Scenario(client)

    client.post(
        f"/delivery/orders/{scenario.order['id']}/pickup/claim",
        headers=scenario.agent_a_headers,
    )
    _set_status(client, scenario.order["id"], "PICKED_UP", scenario.agent_a_headers)

    response = _set_status(client, scenario.order["id"], "RECEIVED", scenario.admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "RECEIVED"


def test_admin_cannot_perform_invalid_transition(client):
    scenario = _Scenario(client)

    response = _set_status(client, scenario.order["id"], "DELIVERED", scenario.admin_headers)
    assert response.status_code == 409


# ---------- Workflow ----------


def test_normal_workflow_including_ironing_branch(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    client.post(
        f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers
    )

    steps = [
        ("PICKED_UP", scenario.agent_a_headers),
        ("RECEIVED", scenario.staff_headers),
        ("SORTING", scenario.staff_headers),
        ("WASHING", scenario.staff_headers),
        ("DRYING", scenario.staff_headers),
        ("IRONING", scenario.staff_headers),
        ("PACKING", scenario.staff_headers),
        ("OUT_FOR_DELIVERY", scenario.staff_headers),
    ]

    for status, headers in steps:
        response = _set_status(client, order_id, status, headers)
        assert response.status_code == 200, f"failed transitioning to {status}"
        assert response.json()["status"] == status

    client.post(
        f"/delivery/orders/{order_id}/delivery/claim", headers=scenario.agent_b_headers
    )
    final = _set_status(client, order_id, "DELIVERED", scenario.agent_b_headers)
    assert final.status_code == 200
    assert final.json()["status"] == "DELIVERED"


def test_received_to_out_for_delivery_works_for_staff(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    client.post(f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers)
    _set_status(client, order_id, "PICKED_UP", scenario.agent_a_headers)
    _set_status(client, order_id, "RECEIVED", scenario.staff_headers)

    response = _set_status(client, order_id, "OUT_FOR_DELIVERY", scenario.staff_headers)
    assert response.status_code == 200


def test_received_to_out_for_delivery_works_for_admin(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    client.post(f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers)
    _set_status(client, order_id, "PICKED_UP", scenario.agent_a_headers)
    _set_status(client, order_id, "RECEIVED", scenario.staff_headers)

    response = _set_status(client, order_id, "OUT_FOR_DELIVERY", scenario.admin_headers)
    assert response.status_code == 200


def test_received_to_out_for_delivery_fails_for_customer(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    client.post(f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers)
    _set_status(client, order_id, "PICKED_UP", scenario.agent_a_headers)
    _set_status(client, order_id, "RECEIVED", scenario.staff_headers)

    response = _set_status(
        client, order_id, "OUT_FOR_DELIVERY", scenario.customer_headers
    )
    assert response.status_code == 403


def test_invalid_transition_remains_rejected(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    client.post(f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers)
    _set_status(client, order_id, "PICKED_UP", scenario.agent_a_headers)
    _set_status(client, order_id, "RECEIVED", scenario.staff_headers)
    _set_status(client, order_id, "SORTING", scenario.staff_headers)

    response = _set_status(client, order_id, "DELIVERED", scenario.staff_headers)
    assert response.status_code == 409


# ---------- Customer cancellation ----------


def test_customer_can_cancel_own_pending_pickup_order(client):
    scenario = _Scenario(client)

    response = _set_status(
        client, scenario.order["id"], "CANCELLED", scenario.customer_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_customer_cannot_cancel_after_picked_up(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    client.post(f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers)
    _set_status(client, order_id, "PICKED_UP", scenario.agent_a_headers)

    response = _set_status(client, order_id, "CANCELLED", scenario.customer_headers)
    assert response.status_code == 403


def test_staff_can_cancel_picked_up_order(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    client.post(f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers)
    _set_status(client, order_id, "PICKED_UP", scenario.agent_a_headers)

    response = _set_status(client, order_id, "CANCELLED", scenario.staff_headers)
    assert response.status_code == 200


def test_customer_cannot_cancel_another_customers_order(client):
    scenario = _Scenario(client)
    other_customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))

    response = _set_status(
        client, scenario.order["id"], "CANCELLED", other_customer_headers
    )
    assert response.status_code == 403


# ---------- Ownership ----------


def test_customer_only_accesses_own_orders(client):
    scenario = _Scenario(client)
    other_customer_headers = _auth_headers(_signup(client, role="CUSTOMER"))

    response = client.get(
        f"/orders/{scenario.order['id']}", headers=other_customer_headers
    )
    assert response.status_code == 403


# ---------- Audit ----------


def test_each_successful_transition_creates_exactly_one_history_row(client):
    scenario = _Scenario(client)
    order_id = scenario.order["id"]

    assert _status_history_count(order_id) == 1  # initial PENDING_PICKUP row

    client.post(f"/delivery/orders/{order_id}/pickup/claim", headers=scenario.agent_a_headers)
    assert _status_history_count(order_id) == 1  # claim does not add history

    _set_status(client, order_id, "PICKED_UP", scenario.agent_a_headers)
    assert _status_history_count(order_id) == 2

    _set_status(client, order_id, "RECEIVED", scenario.staff_headers)
    assert _status_history_count(order_id) == 3
