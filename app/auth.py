from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from app.db import get_db
from app.schemas import Token, UserCreate, UserResponse, UserLogin
from app.services import create_user, authenticate_user, get_user
from app.security import create_access_token, verify_token
from app.config import settings
from app.models import User 

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["authentication"])


# -------------------- Dependency -------------------- #
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = await verify_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user(db, user_id=token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account deactivated"
        )
    
    request.state.current_user = user
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    
    token_data = await verify_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        return None
    
    return get_user(db, user_id=token_data.user_id)


# -------------------- Routes -------------------- #
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (Public)"""
    existing_user = get_user(db, user.user_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    return create_user(db, user)


@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate and return JWT token (Public)"""
    user = authenticate_user(db, form_data.user_id, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user_id or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.user_id}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}