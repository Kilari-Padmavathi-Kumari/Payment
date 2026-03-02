import asyncio
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.logger import logger
from app.models import Order, User, Wallet
from app.security import get_password_hash, verify_password


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def create_user(db, payload):
    logger.info("Creating user: user_id=%s email=%s", payload.user_id, payload.email)
    existing = (
        db.query(User)
        .filter(or_(User.user_id == payload.user_id, User.email == payload.email))
        .first()
    )
    if existing:
        logger.warning("User create blocked: duplicate user_id/email")
        raise HTTPException(status_code=400, detail="User already exists")

    row = User(
        user_id=payload.user_id,
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
    )

    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info("User created successfully: user_id=%s", row.user_id)
        return row
    except IntegrityError:
        db.rollback()
        logger.exception("Database integrity error while creating user")
        raise HTTPException(status_code=400, detail="User already exists")


def authenticate_user(db, user_id, email, password):
    if not user_id and not email:
        logger.warning("Authenticate failed: no user_id/email provided")
        return None

    query = db.query(User)
    if user_id and email:
        user = query.filter(or_(User.user_id == user_id, User.email == email)).first()
    elif user_id:
        user = query.filter(User.user_id == user_id).first()
    else:
        user = query.filter(User.email == email).first()

    if not user or not user.is_active:
        logger.warning("Authenticate failed: user not found or inactive")
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning("Authenticate failed: password mismatch")
        return None

    logger.info("Authenticate success: user_id=%s", user.user_id)
    return user


def get_user(db, user_id):
    return db.query(User).filter(User.user_id == user_id).first()


def list_users(db, skip=0, limit=100):
    return db.query(User).offset(skip).limit(limit).all()


def create_order(db, payload):
    logger.info("Creating order: customer_id=%s amount=%s", payload.customer_id, payload.amount)
    if payload.idempotency_key:
        existing = db.query(Order).filter(Order.idempotency_key == payload.idempotency_key).first()
        if existing:
            logger.info("Order idempotency hit: key=%s order_id=%s", payload.idempotency_key, existing.id)
            return existing

    row = Order(
        id=str(uuid.uuid4()),
        customer_id=payload.customer_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=payload.idempotency_key,
        status="created",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("Order created: order_id=%s", row.id)
    return row


async def handle_settlement_window(order_id, window_seconds):
    logger.info("Settlement window started for order_id=%s", order_id)
    elapsed = 0.0
    while elapsed < window_seconds:
        await asyncio.sleep(0.5)
        elapsed += 0.5
    logger.info("Settlement window completed for order_id=%s", order_id)


def get_orders_by_customer(db, customer_id):
    return (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .all()
    )


def get_wallet(db, customer_id):
    logger.info("Fetching wallet: customer_id=%s", customer_id)
    wallet = db.query(Wallet).filter(Wallet.customer_id == customer_id).first()
    if wallet:
        logger.info("Wallet found: customer_id=%s", customer_id)
        return wallet

    wallet = Wallet(customer_id=customer_id, balance=0)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    logger.info("Wallet auto-created: customer_id=%s", customer_id)
    return wallet


def credit_wallet(db, customer_id, amount):
    logger.info("Credit wallet request: customer_id=%s amount=%s", customer_id, amount)
    try:
        wallet = (
            db.query(Wallet)
            .filter(Wallet.customer_id == customer_id)
            .with_for_update()
            .first()
        )

        if not wallet:
            wallet = Wallet(customer_id=customer_id, balance=0)
            db.add(wallet)

        wallet.balance = float(wallet.balance) + amount
        wallet.updated_at = datetime.now(timezone.utc)

        logger.info(
            "AUDIT wallet_credit customer_id=%s amount=%s balance=%s at=%s",
            customer_id,
            amount,
            wallet.balance,
            _utc_now(),
        )

        db.commit()
        db.refresh(wallet)
        logger.info("Credit wallet success: customer_id=%s balance=%s", customer_id, wallet.balance)
        return wallet
    except Exception:
        db.rollback()
        logger.exception("Credit wallet failed: customer_id=%s", customer_id)
        raise


def debit_wallet(db, customer_id, amount):
    logger.info("Debit wallet request: customer_id=%s amount=%s", customer_id, amount)
    wallet = (
        db.query(Wallet)
        .filter(Wallet.customer_id == customer_id)
        .with_for_update()
        .first()
    )
    if not wallet:
        wallet = Wallet(customer_id=customer_id, balance=0)
        db.add(wallet)

    current_balance = float(wallet.balance)
    if current_balance < amount:
        logger.warning(
            "Debit wallet blocked: insufficient balance customer_id=%s balance=%s amount=%s",
            customer_id,
            current_balance,
            amount,
        )
        raise ValueError("Insufficient wallet balance")

    try:
        wallet.balance = current_balance - amount
        wallet.updated_at = datetime.now(timezone.utc)

        logger.info(
            "AUDIT wallet_debit customer_id=%s amount=%s balance=%s at=%s",
            customer_id,
            amount,
            wallet.balance,
            _utc_now(),
        )

        db.commit()
        db.refresh(wallet)
        logger.info("Debit wallet success: customer_id=%s balance=%s", customer_id, wallet.balance)
        return wallet
    except Exception:
        db.rollback()
        logger.exception("Debit wallet failed: customer_id=%s", customer_id)
        raise
