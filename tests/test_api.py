import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
os.environ["SECRET_KEY"] = "test-secret-key-please-change"

from app.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_info_endpoints(client: TestClient):
    health = client.get("/")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    info = client.get("/api")
    assert info.status_code == 200
    assert "auth" in info.json()


def test_auth_register_login_flow(client: TestClient):
    register_payload = {
        "user_id": "CUST-001",
        "email": "cust1@example.com",
        "full_name": "Customer One",
        "phone": "+15550000001",
        "password": "password123",
    }

    register = client.post("/api/auth/register", json=register_payload)
    assert register.status_code == 201, register.text

    login = client.post(
        "/api/auth/login",
        json={"email": "cust1@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    assert "access_token" in login.json()


def test_auth_invalid_login_and_duplicate_registration(client: TestClient):
    payload = {
        "user_id": "CUST-010",
        "email": "cust10@example.com",
        "full_name": "Customer Ten",
        "phone": "+15550000010",
        "password": "password123",
    }
    register = client.post("/api/auth/register", json=payload)
    assert register.status_code == 201, register.text

    duplicate = client.post("/api/auth/register", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "User already exists"

    invalid_login = client.post(
        "/api/auth/login",
        json={"email": "cust10@example.com", "password": "wrong-password"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["detail"] == "Invalid credentials"


def test_auth_required_for_protected_endpoints(client: TestClient):
    users = client.get("/api/users")
    assert users.status_code == 401
    assert users.headers["www-authenticate"] == "Bearer"
    assert "Authentication required" in users.json()["detail"]

    orders = client.get("/api/orders", params={"customer_id": "CUST-001"})
    assert orders.status_code == 401

    wallet = client.get("/api/wallet/CUST-001")
    assert wallet.status_code == 401


def test_users_orders_wallet_endpoints(client: TestClient):
    register_payload = {
        "user_id": "CUST-002",
        "email": "cust2@example.com",
        "full_name": "Customer Two",
        "phone": "+15550000002",
        "password": "password123",
    }
    register = client.post("/api/auth/register", json=register_payload)
    assert register.status_code == 201, register.text

    login = client.post(
        "/api/auth/login",
        json={"email": "cust2@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    users = client.get("/api/users", headers=headers)
    assert users.status_code == 200
    assert len(users.json()) == 1

    user = client.get("/api/users/CUST-002", headers=headers)
    assert user.status_code == 200

    order = client.post(
        "/api/orders",
        headers=headers,
        json={
            "customer_id": "CUST-002",
            "amount": 100.5,
            "currency": "INR",
            "idempotency_key": "idem-001",
        },
    )
    assert order.status_code == 201, order.text

    orders = client.get("/api/orders", headers=headers, params={"customer_id": "CUST-002"})
    assert orders.status_code == 200
    assert len(orders.json()) == 1

    credit = client.post(
        "/api/wallet/CUST-002/credit",
        headers=headers,
        json={"amount": 200},
    )
    assert credit.status_code == 200
    assert credit.json()["balance"] == 200.0

    debit = client.post(
        "/api/wallet/CUST-002/debit",
        headers=headers,
        json={"amount": 50},
    )
    assert debit.status_code == 200
    assert debit.json()["balance"] == 150.0

    wallet = client.get("/api/wallet/CUST-002", headers=headers)
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 150.0


def test_order_idempotency_and_wallet_insufficient_balance(client: TestClient):
    register_payload = {
        "user_id": "CUST-005",
        "email": "cust5@example.com",
        "full_name": "Customer Five",
        "phone": "+15550000005",
        "password": "password123",
    }
    register = client.post("/api/auth/register", json=register_payload)
    assert register.status_code == 201, register.text

    login = client.post(
        "/api/auth/login",
        json={"email": "cust5@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "customer_id": "CUST-005",
        "amount": 111.0,
        "currency": "INR",
        "idempotency_key": "idem-xyz",
    }
    first = client.post("/api/orders", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    second = client.post("/api/orders", headers=headers, json=payload)
    assert second.status_code == 201, second.text
    assert first.json()["order_id"] == second.json()["order_id"]

    debit = client.post(
        "/api/wallet/CUST-005/debit",
        headers=headers,
        json={"amount": 1},
    )
    assert debit.status_code == 400
    assert debit.json()["detail"] == "Insufficient wallet balance"


def test_forbidden_cross_customer_access(client: TestClient):
    register_a = client.post(
        "/api/auth/register",
        json={
            "user_id": "CUST-003",
            "email": "cust3@example.com",
            "full_name": "Customer Three",
            "phone": "+15550000003",
            "password": "password123",
        },
    )
    assert register_a.status_code == 201, register_a.text

    register_b = client.post(
        "/api/auth/register",
        json={
            "user_id": "CUST-004",
            "email": "cust4@example.com",
            "full_name": "Customer Four",
            "phone": "+15550000004",
            "password": "password123",
        },
    )
    assert register_b.status_code == 201, register_b.text

    login = client.post(
        "/api/auth/login",
        json={"email": "cust3@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    forbidden_order = client.post(
        "/api/orders",
        headers=headers,
        json={"customer_id": "CUST-004", "amount": 10, "currency": "INR"},
    )
    assert forbidden_order.status_code == 403
