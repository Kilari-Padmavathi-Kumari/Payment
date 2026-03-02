from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.db import get_db
from app.schemas import Token, UserCreate, UserLogin, UserResponse
from app.security import create_access_token, verify_token
from app.services import authenticate_user, create_user, get_user
from app.logger import logger

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
):
    logger.info("Validating access token for protected endpoint")
    if not credentials:
        logger.warning("Auth failed: missing bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = verify_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        logger.warning("Auth failed: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user(db, token_data.user_id)
    if not user:
        logger.warning("Auth failed: token user not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.is_active:
        logger.warning("Auth failed: inactive account user_id=%s", token_data.user_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account deactivated")

    request.state.current_user = user
    logger.info("Authenticated user_id=%s", user.user_id)
    return user


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: UserCreate, db=Depends(get_db)):
    logger.info("Register request for user_id=%s", payload.user_id)
    return create_user(db, payload)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db=Depends(get_db)):
    if not payload.user_id and not payload.email:
        logger.warning("Login failed: neither user_id nor email provided")
        raise HTTPException(status_code=400, detail="Provide user_id or email")

    login_identity = payload.user_id if payload.user_id else payload.email
    logger.info("Login request for identity=%s", login_identity)
    user = authenticate_user(db, payload.user_id, payload.email, payload.password)
    if not user:
        logger.warning("Login failed for identity=%s", login_identity)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": user.user_id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("Login successful for user_id=%s", user.user_id)
    return Token(access_token=token)
