from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db import get_db
from app.schemas import WalletOperation, WalletResponse
from app import services
from app.logger import logger
from app.auth import get_current_user
from app.models import User


router = APIRouter(prefix="/wallet", tags=["wallet"])


# ========================
# CONSTANTS
# ========================

UNAUTHORIZED_MODIFY_WALLET = "Not authorized to modify this wallet"
UNAUTHORIZED_VIEW_WALLET = "Not authorized to view this wallet"
INVALID_AMOUNT_MESSAGE = "Amount must be positive"


# ========================
# HELPER FUNCTION
# ========================

def authorize_wallet_access(customer_id: str, current_user: User, request_id: str, action: str):
    if customer_id != current_user.user_id:
        logger.warning(
            f"[{request_id}] Wallet {action} denied: "
            f"{current_user.user_id} tried to access wallet for {customer_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=UNAUTHORIZED_MODIFY_WALLET
        )


# ========================
# CREDIT WALLET
# ========================

@router.post("/{customer_id}/credit", response_model=WalletResponse)
def credit_wallet(
    customer_id: str,
    operation: WalletOperation,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"

    authorize_wallet_access(customer_id, current_user, request_id, "credit")

    if operation.amount <= 0:
        logger.warning(f"[{request_id}] Wallet credit failed: invalid amount={operation.amount}")
        raise HTTPException(status_code=400, detail=INVALID_AMOUNT_MESSAGE)

    logger.info(f"[{request_id}] Wallet credit request customer_id={customer_id} amount={operation.amount}")

    try:
        wallet = services.credit_wallet(db, customer_id, operation.amount)
        balance_value = float(Decimal(str(wallet.balance)))

        logger.info(
            f"[{request_id}] Wallet credit successful "
            f"customer_id={customer_id} new_balance={balance_value}"
        )

        return WalletResponse(customer_id=wallet.customer_id, balance=balance_value)

    except ValueError as e:
        logger.warning(
            f"[{request_id}] Wallet credit failed "
            f"customer_id={customer_id} reason={str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(
            f"[{request_id}] Wallet credit error "
            f"customer_id={customer_id}: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Wallet credit failed")


# ========================
# DEBIT WALLET
# ========================

@router.post("/{customer_id}/debit", response_model=WalletResponse)
def debit_wallet(
    customer_id: str,
    operation: WalletOperation,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"

    authorize_wallet_access(customer_id, current_user, request_id, "debit")

    if operation.amount <= 0:
        logger.warning(f"[{request_id}] Wallet debit failed: invalid amount={operation.amount}")
        raise HTTPException(status_code=400, detail=INVALID_AMOUNT_MESSAGE)

    logger.info(f"[{request_id}] Wallet debit request customer_id={customer_id} amount={operation.amount}")

    try:
        wallet = services.debit_wallet(db, customer_id, operation.amount)
        balance_value = float(Decimal(str(wallet.balance)))

        logger.info(
            f"[{request_id}] Wallet debit successful "
            f"customer_id={customer_id} new_balance={balance_value}"
        )

        return WalletResponse(customer_id=wallet.customer_id, balance=balance_value)

    except ValueError as e:
        logger.warning(
            f"[{request_id}] Wallet debit failed "
            f"customer_id={customer_id} reason={str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(
            f"[{request_id}] Wallet debit error "
            f"customer_id={customer_id}: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Wallet debit failed")


# ========================
# GET WALLET
# ========================

@router.get("/{customer_id}", response_model=WalletResponse)
def get_wallet(
    customer_id: str,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"

    if customer_id != current_user.user_id:
        logger.warning(
            f"[{request_id}] Wallet fetch denied: "
            f"{current_user.user_id} tried to access wallet for {customer_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=UNAUTHORIZED_VIEW_WALLET,
        )

    logger.info(f"[{request_id}] Wallet fetch request customer_id={customer_id}")

    try:
        wallet = services.get_wallet(db, customer_id)
        balance_value = float(Decimal(str(wallet.balance)))

        logger.info(
            f"[{request_id}] Wallet fetch successful "
            f"customer_id={customer_id} balance={balance_value}"
        )

        return WalletResponse(customer_id=wallet.customer_id, balance=balance_value)

    except Exception as e:
        logger.error(
            f"[{request_id}] Wallet fetch error "
            f"customer_id={customer_id}: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve wallet")
