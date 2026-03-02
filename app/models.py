from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(100), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    orders = relationship("Order", back_populates="user")
    wallet = relationship("Wallet", back_populates="user", uselist=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(100), ForeignKey("users.user_id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    idempotency_key = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="created")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="orders")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_order_amount_positive"),
    )


class Wallet(Base):
    __tablename__ = "wallets"

    customer_id = Column(String(100), ForeignKey("users.user_id"), primary_key=True)
    balance = Column(Numeric(10, 2), nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="wallet")

    __table_args__ = (
        CheckConstraint("balance >= 0", name="check_wallet_balance_non_negative"),
    )
