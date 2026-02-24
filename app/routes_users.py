from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.schemas import UserCreate, UserResponse, UserDetail
from app import services
from app.auth import get_current_user  
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user (Sign Up).
    Public endpoint - or use POST /api/auth/register for clarity.
    """
    try:
        new_user = services.create_user(db, user)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions from services
        raise


@router.get("/{user_id}", response_model=UserDetail)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  
):
    """
    Get user details by user ID.
    Protected: Requires valid JWT token.
    Authorization: Users can view own profile; admins can view any.
    """
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's data"
        )
    
    # Fetch and return user
    user = services.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=List[UserDetail])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  
):
    """
    List all users.
    Protected: Requires valid JWT token.
    Authorization: Currently allows any authenticated user (add admin check if needed).
    """
    
    users = services.list_users(db, skip=skip, limit=limit)
    return users