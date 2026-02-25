from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: bool = True

class UserCreate(UserBase):
    user_id: str = Field(..., min_length=3, max_length=100, pattern=r'^[A-Z]+-\d+$')
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "CUST-001",
                "email": "customer@example.com",
                "full_name": "John Doe",
                "phone": "+91-9876543210",
                "password": "password123"
            }
        }

class User(UserBase):
    """Schema matching the database User model - used internally"""
    user_id: str
    hashed_password: Optional[str] = None
    created_at: datetime
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    user_id: str = Field(..., pattern=r'^[A-Z]+-\d+$')
    password: str
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "CUST-001",
                "password": "password123"
            }
        }

class UserResponse(UserBase):
    user_id: str
    created_at: datetime
    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"user_id": "CUST-001", "email": "customer@example.com"}}


class UserDetail(UserResponse):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None

class OrderCreate(BaseModel):
    customer_id: str = Field(..., min_length=3, max_length=100)
    amount: float = Field(..., gt=0, le=1000000)
    currency: str = Field(default="INR", pattern=r'^[A-Z]{3}$')
    idempotency_key: Optional[str] = Field(None, max_length=255)

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "CUST-001",
                "amount": 499.99,
                "currency": "INR",
                "idempotency_key": "order-abc-123"
            }
        }


class OrderResponse(BaseModel):
    order_id: UUID
    status: str

    class Config:
        from_attributes = True


class OrderDetail(BaseModel):
    id: UUID
    customer_id: str
    amount: float
    currency: str
    status: str
    idempotency_key: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WalletOperation(BaseModel):
    amount: float = Field(..., gt=0, le=100000)

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1000.00
            }
        }


class WalletResponse(BaseModel):
    customer_id: str
    balance: float

    class Config:
        from_attributes = True


class WalletDetail(BaseModel):
    customer_id: str
    balance: float
    updated_at: datetime

    class Config:
        from_attributes = True
