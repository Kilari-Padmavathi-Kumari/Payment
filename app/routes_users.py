import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.schemas import UserCreate, UserResponse, UserDetail
from app import services
from app.auth import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"API create_user called for user_id={user.user_id}")
    try:
        new_user = services.create_user(db, user)
        logger.info(f"User created user_id={user.user_id}")
        return new_user
    except ValueError as e:
        logger.warning(f"User creation failed user_id={user.user_id} reason={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        logger.exception(f"HTTPException during user creation user_id={user.user_id}")
        raise

@router.get("/{user_id}", response_model=UserDetail)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User fetch requested for user_id={user_id} by {current_user.user_id}")
    if current_user.user_id != user_id:
        logger.warning(f"Unauthorized access attempt: {current_user.user_id} -> {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's data"
        )
    user = services.get_user(db, user_id)
    if not user:
        logger.warning(f"User not found user_id={user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User data returned for user_id={user_id}")
    return user

@router.get("", response_model=List[UserDetail])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User list requested by {current_user.user_id} skip={skip} limit={limit}")
    users = services.list_users(db, skip=skip, limit=limit)
    logger.info(f"{len(users)} users returned to {current_user.user_id}")
    return users