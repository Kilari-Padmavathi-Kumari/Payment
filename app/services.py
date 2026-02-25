import logging
import asyncio
import uuid
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models import Order, Wallet, User
from app.schemas import OrderCreate, UserCreate, UserResponse
from app.config import settings
from app.security import get_password_hash, verify_password
from app.logger import logger  # â† Centralized logger

def create_user(db: Session, user_data: UserCreate) -> UserResponse:
    """Create a new user with hashed password"""
    logger.info(f"Creating user in DB user_id={user_data.user_id}")

    existing = db.query(User).filter(
        (User.user_id == user_data.user_id) |
        (User.email == user_data.email)
    ).first()

    if existing:
        logger.warning(f"Duplicate registration attempt user_id={user_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID or Email already registered"
        )

    db_user = User(
        user_id=user_data.user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        phone=user_data.phone,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User successfully stored in DB user_id={user_data.user_id}")
    except IntegrityError:
        db.rollback()
        logger.exception(f"Integrity error while creating user user_id={user_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed - duplicate entry"
        )

    return UserResponse.model_validate(db_user)


def authenticate_user(db: Session, user_id: str, password: str) -> Optional[User]:
    """Verify credentials and return user if valid"""
    logger.info(f"Authenticating user user_id={user_id}")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"Authentication failed - user not found user_id={user_id}")
        return None
    if not user.is_active:
        logger.warning(f"Authentication failed - inactive account user_id={user_id}")
        return None
    if user.hashed_password is None:
        logger.warning(f"Authentication failed - no password set user_id={user_id}")
        return None
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed - wrong password user_id={user_id}")
        return None

    logger.info(f"Authentication successful user_id={user_id}")
    return user


def get_user(db: Session, user_id: str) -> User:
    """Get user by ID"""
    logger.info(f"Fetching user from DB user_id={user_id}")
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        logger.info(f"User found user_id={user_id}")
    else:
        logger.warning(f"User not found user_id={user_id}")
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100):
    """List all users with pagination"""
    logger.info(f"Listing users skip={skip} limit={limit}")
    users = db.query(User).offset(skip).limit(limit).all()
    logger.info(f"{len(users)} users fetched from DB")
    return users

def create_order_immediate(db: Session, order_data: OrderCreate) -> Order:
    """
    Create order WITHOUT blocking settlement window.
    Settlement handling is offloaded to background task.
    """
    logger.info(
        f"DB: Creating order customer_id={order_data.customer_id} "
        f"amount={order_data.amount} currency={order_data.currency}"
    )

    # Idempotency check with logging
    if settings.enable_strict_idempotency_check and order_data.idempotency_key:
        existing = db.query(Order).filter(
            Order.idempotency_key == order_data.idempotency_key
        ).first()
        if existing:
            logger.info(
                f"DB: Idempotency hit - returning existing order_id={existing.id} "
                f"for key={order_data.idempotency_key}"
            )
            return existing

    order = Order(
        id=str(uuid.uuid4()),
        customer_id=order_data.customer_id,
        amount=order_data.amount,
        currency=order_data.currency,
        idempotency_key=order_data.idempotency_key,
        status="created"
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    logger.info(f"DB: Order created successfully order_id={order.id}")
    return order

async def handle_settlement_window(order_id: uuid.UUID, window_seconds: float):
    """
    Background task to handle payment gateway settlement window.
    Run this with FastAPI BackgroundTasks or Celery.
    """
    logger.info(f"BG_TASK: Starting settlement window for order_id={order_id} duration={window_seconds}s")

    poll_interval = 0.5
    elapsed = 0.0

    while elapsed < window_seconds:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        # In production: poll payment gateway status here
        # response = await payment_gateway.get_status(order_id)
        # if response.status == "settled": break

    logger.info(f"BG_TASK: Settlement window completed for order_id={order_id}")
    # Update order status if needed: order.status = "settled"


def create_order(db: Session, order_data: OrderCreate) -> Order:
    """
    Legacy wrapper (blocking settlement window).
    """
    order = create_order_immediate(db, order_data)
    if settings.transaction_settlement_window > 0:
        logger.info(
            f"Starting synchronous settlement window "
            f"for order_id={order.id} "
            f"duration={settings.transaction_settlement_window}s"
        )
        poll_interval = 0.5
        elapsed = 0.0
        while elapsed < settings.transaction_settlement_window:
            time.sleep(poll_interval)
            elapsed += poll_interval
        logger.info(f"Settlement window completed for order_id={order.id}")
    return order


def get_orders_by_customer(db: Session, customer_id: str):
    """
    Retrieve all orders for a customer - READ-ONLY operation.
    Added safeguard: expire all pending changes to prevent accidental writes.
    """
    logger.info(f"DB: READ-ONLY fetch orders for customer_id={customer_id}")

    # SAFEGUARD: Expire any pending changes in session to ensure pure read
    # This prevents autoflush from accidentally committing pending INSERTs/UPDATEs
    db.expunge_all()

    orders = db.query(Order).filter(Order.customer_id == customer_id).all()

    logger.info(f"DB: Found {len(orders)} orders for customer_id={customer_id}")
    return orders

def get_wallet(db: Session, customer_id: str) -> Wallet:
    """Get wallet for a customer, create if doesn't exist (with logging)"""
    wallet = db.query(Wallet).filter(Wallet.customer_id == customer_id).first()
    if not wallet:
        logger.info(f"DB: Auto-creating wallet for new customer_id={customer_id}")
        wallet = Wallet(customer_id=customer_id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def credit_wallet(db: Session, customer_id: str, amount: float) -> Wallet:
    """
    Credit wallet with row-level locking for concurrency safety.
    Uses SELECT FOR UPDATE to prevent race conditions.
    """
    logger.info(f"DB: Credit wallet customer_id={customer_id} amount={amount}")
   
    try:
        # Lock the wallet row for this transaction (prevents race conditions)
        wallet = db.query(Wallet).filter(
            Wallet.customer_id == customer_id
        ).with_for_update().first()

        if not wallet:
            wallet = Wallet(customer_id=customer_id, balance=0)
            db.add(wallet)

        old_balance = float(wallet.balance)
        new_balance = old_balance + amount

        logger.debug(f"DB: Balance update {old_balance} + {amount} = {new_balance}")

        # Audit log for financial operation (compliance requirement)
        logger.info(
            f"AUDIT: WALLET_CREDIT customer_id={customer_id} "
            f"old_balance={old_balance} amount={amount} new_balance={new_balance} "
            f"timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        wallet.balance = new_balance
        db.commit()
        db.refresh(wallet)

        logger.info(f"DB: Wallet credited successfully customer_id={customer_id} new_balance={new_balance}")
        return wallet

    except Exception as e:
        db.rollback()
        logger.error(f"DB: Wallet credit failed customer_id={customer_id}: {type(e).__name__}", exc_info=True)
        raise


def debit_wallet(db: Session, customer_id: str, amount: float) -> Wallet:
    """
    Debit wallet with balance validation and row-level locking.
    Uses SELECT FOR UPDATE to prevent race conditions.
    """
    logger.info(f"DB: Debit wallet customer_id={customer_id} amount={amount}")

    try:
        # Lock the wallet row for this transaction (prevents race conditions)
        wallet = db.query(Wallet).filter(
            Wallet.customer_id == customer_id
        ).with_for_update().first()

        if not wallet:
            logger.warning(f"DB: Wallet not found for debit customer_id={customer_id}")
            raise ValueError("Wallet not found")

        current_balance = float(wallet.balance)

        # Business rule validation: sufficient funds check
        if current_balance < amount:
            logger.warning(f"DB: Insufficient balance customer_id={customer_id} have={current_balance} need={amount}")
            raise ValueError("Insufficient balance")

        old_balance = current_balance
        new_balance = old_balance - amount

        logger.debug(f"DB: Balance update {old_balance} - {amount} = {new_balance}")

        # Audit log for financial operation (compliance requirement)
        logger.info(
            f"AUDIT: WALLET_DEBIT customer_id={customer_id} "
            f"old_balance={old_balance} amount={amount} new_balance={new_balance} "
            f"timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        wallet.balance = new_balance
        db.commit()
        db.refresh(wallet)
       
        logger.info(f"DB: Wallet debited successfully customer_id={customer_id} new_balance={new_balance}")
        return wallet

    except ValueError:
        # Don't rollback on business rule failures (expected behavior)
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"DB: Wallet debit failed customer_id={customer_id}: {type(e).__name__}", exc_info=True)
        raise
