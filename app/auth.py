import logging
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

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        logger.warning("Authentication failed: No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info("Bearer token received, validating")
    token_data = verify_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        logger.warning("Authentication failed: Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info(f"Token valid for user_id={token_data.user_id}")
    user = get_user(db, user_id=token_data.user_id)
    if not user:
        logger.warning(f"Authentication failed: User not found user_id={token_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if not user.is_active:
        logger.warning(f"Authentication failed: Inactive account user_id={user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account deactivated"
        )
    logger.info(f"User authenticated successfully user_id={user.user_id}")
    request.state.current_user = user
    return user

def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        logger.debug("Optional auth: No credentials provided")
        return None
    token_data = verify_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        logger.debug("Optional auth: Invalid token")
        return None
    logger.debug(f"Optional auth: Valid token user_id={token_data.user_id}")
    return get_user(db, user_id=token_data.user_id)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for user_id={user.user_id}")
    created_user = create_user(db, user)
    logger.info(f"User registered successfully user_id={user.user_id}")
    return created_user

@router.post("/login", response_model=Token)
def login(form_data: UserLogin, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for user_id={form_data.user_id}")
    user = authenticate_user(db, form_data.user_id, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user_id={form_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user_id or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_id},
        expires_delta=access_token_expires
    )
    logger.info(f"Login successful user_id={user.user_id}")
    return {"access_token": access_token, "token_type": "bearer"}