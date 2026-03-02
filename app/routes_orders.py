from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import services
from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas import OrderCreate, OrderDetail, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
def create_order_endpoint(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create orders for this customer",
        )

    order = services.create_order(db, payload)

    if settings.transaction_settlement_window > 0:
        background_tasks.add_task(
            services.handle_settlement_window,
            order_id=order.id,
            window_seconds=settings.transaction_settlement_window,
        )

    return OrderResponse(order_id=order.id, status=order.status)


@router.get("", response_model=List[OrderDetail])
def list_orders_endpoint(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view orders for this customer",
        )

    return services.get_orders_by_customer(db, customer_id)
