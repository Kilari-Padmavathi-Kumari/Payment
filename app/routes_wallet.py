from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import services
from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import WalletOperation, WalletResponse

router = APIRouter(prefix="/wallet", tags=["wallet"])


def _authorize(customer_id: str, current_user: User):
    if customer_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post("/{customer_id}/credit", response_model=WalletResponse)
def credit_wallet_endpoint(
    customer_id: str,
    payload: WalletOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize(customer_id, current_user)

    try:
        wallet = services.credit_wallet(db, customer_id, payload.amount)
    except Exception:
        raise HTTPException(status_code=500, detail="Wallet credit failed")

    return WalletResponse(customer_id=wallet.customer_id, balance=float(wallet.balance))


@router.post("/{customer_id}/debit", response_model=WalletResponse)
def debit_wallet_endpoint(
    customer_id: str,
    payload: WalletOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize(customer_id, current_user)

    try:
        wallet = services.debit_wallet(db, customer_id, payload.amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Wallet debit failed")

    return WalletResponse(customer_id=wallet.customer_id, balance=float(wallet.balance))


@router.get("/{customer_id}", response_model=WalletResponse)
def get_wallet_endpoint(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize(customer_id, current_user)

    wallet = services.get_wallet(db, customer_id)
    return WalletResponse(customer_id=wallet.customer_id, balance=float(wallet.balance))
