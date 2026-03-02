from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: bool = True


class UserCreate(UserBase):
    user_id: str = Field(..., min_length=3, max_length=100, pattern=r"^[A-Z]+-\d+$")
    password: str = Field(..., min_length=8)


class UserInDB(UserBase):
    user_id: str
    hashed_password: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    user_id: Optional[str] = Field(None, pattern=r"^[A-Z]+-\d+$")
    email: Optional[EmailStr] = None
    password: str


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    phone: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


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
    currency: str = Field("INR", pattern=r"^[A-Z]{3}$")
    idempotency_key: Optional[str] = Field(None, max_length=255)


class OrderResponse(BaseModel):
    order_id: str
    status: str


class OrderDetail(BaseModel):
    id: str
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
