#!/usr/bin/env python3
import argparse
import asyncio

import httpx

BASE_URL = "http://localhost:8000/api"
DEFAULT_PASSWORD = "password123"


def _json_or_text(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return response.text


def normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    return normalized if normalized.endswith("/api") else f"{normalized}/api"


async def seed_user(
    client: httpx.AsyncClient,
    user_id: str,
    email: str,
    full_name: str,
    phone: str | None = None,
    password: str = DEFAULT_PASSWORD,
) -> bool:
    """Create a user (or proceed if already present)."""
    print(f"Creating user {user_id}...")

    response = await client.post(
        "/auth/register",
        json={
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "password": password,
        },
    )

    if response.status_code == 201:
        data = response.json()
        print(f"OK User created: {data['user_id']} - {data['full_name']} ({data['email']})")
        return True
    if response.status_code == 400:
        print(f"OK User {user_id} already exists")
        return True

    print(f"X Failed to create user: {response.status_code}")
    print(f"  {_json_or_text(response)}")
    return False


async def login_user(
    client: httpx.AsyncClient,
    user_id: str,
    password: str = DEFAULT_PASSWORD,
) -> dict[str, str] | None:
    """Login and return auth headers."""
    response = await client.post(
        "/auth/login",
        json={"user_id": user_id, "password": password},
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    print(f"X Failed to login user {user_id}: {response.status_code}")
    print(f"  {_json_or_text(response)}")
    return None


async def seed_wallet(
    client: httpx.AsyncClient,
    customer_id: str,
    headers: dict[str, str],
    initial_balance: float = 1000.0,
) -> bool:
    """Initialize a wallet with starting balance."""
    print(f"Seeding wallet for {customer_id} with balance {initial_balance}...")

    response = await client.post(
        f"/wallet/{customer_id}/credit",
        json={"amount": initial_balance},
        headers=headers,
    )

    if response.status_code == 200:
        data = response.json()
        print(f"OK Wallet updated: {data['customer_id']} - Balance: {data['balance']}")
        return True

    print(f"X Failed to update wallet: {response.status_code}")
    print(f"  {_json_or_text(response)}")
    return False


async def seed_orders(
    client: httpx.AsyncClient,
    customer_id: str,
    headers: dict[str, str],
    count: int = 3,
):
    """Create sample orders."""
    print(f"\nCreating {count} sample orders for {customer_id}...")

    for i in range(count):
        amount = 100.0 + (i * 50)
        response = await client.post(
            "/orders",
            json={
                "customer_id": customer_id,
                "amount": amount,
                "currency": "INR",
                "idempotency_key": f"seed-order-{customer_id}-{i}",
            },
            headers=headers,
            timeout=10.0,
        )

        if response.status_code == 201:
            data = response.json()
            print(f"OK Order created: {data['order_id']}")
        else:
            print(f"X Failed to create order: {response.status_code}")
            print(f"  {_json_or_text(response)}")


async def seed_multiple_users(client: httpx.AsyncClient):
    """Seed multiple users with wallets and orders."""
    users = [
        ("CUST-001", "john.doe@example.com", "John Doe", "+91-9876543210"),
        ("CUST-002", "jane.smith@example.com", "Jane Smith", "+91-9876543211"),
        ("CUST-003", "bob.wilson@example.com", "Bob Wilson", "+91-9876543212"),
    ]

    print("=" * 60)
    print("Seeding multiple users")
    print("=" * 60)

    for user_id, email, full_name, phone in users:
        print(f"\n--- Processing {user_id} ---")
        if await seed_user(client, user_id, email, full_name, phone):
            headers = await login_user(client, user_id)
            if not headers:
                continue
            await seed_wallet(client, user_id, headers, 1000.0 + (int(user_id.split("-")[1]) * 500))
            await seed_orders(client, user_id, headers, 2)


async def main():
    parser = argparse.ArgumentParser(description="Seed users, wallets, and orders")
    parser.add_argument("--all", action="store_true", help="Seed multiple predefined users")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("customer_id", nargs="?", default="CUST-001")
    parser.add_argument("email", nargs="?")
    parser.add_argument("full_name", nargs="?", default="Test User")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)

    async with httpx.AsyncClient(base_url=base_url) as client:
        if args.all:
            await seed_multiple_users(client)
            return

        customer_id = args.customer_id
        email = args.email or f"{customer_id.lower()}@example.com"
        full_name = args.full_name

        print(f"Starting data seeding for customer: {customer_id}\n")

        if await seed_user(client, customer_id, email, full_name, "+91-9876543210"):
            headers = await login_user(client, customer_id)
            if headers:
                await seed_wallet(client, customer_id, headers, 1000.0)
                await seed_orders(client, customer_id, headers, 3)

        print("\nOK Seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())