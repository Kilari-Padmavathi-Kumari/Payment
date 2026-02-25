from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging
from app.config import settings
from app.schemas import TokenData

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed password.
    Never log passwords.
    """
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug("Password verification executed")
        return result
    except Exception:
        logger.exception("Error during password verification")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash password using bcrypt via passlib.
    Never log raw password.
    """
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hashing completed successfully")
        return hashed
    except Exception:
        logger.exception("Error while hashing password")
        raise

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    Logs only user identifier (never token itself).
    """
    try:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
    expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
        to_encode.update({"exp": expire, "type": "access"})
        token = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        logger.info(f"Access token created for user_id={data.get('sub')}")
        return token
    except Exception:
        logger.exception("Failed to create access token")
        raise

def verify_token(token: str) -> Optional[TokenData]:
    """
    Validate JWT and extract user_id.
    Does NOT log token content.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None:
            logger.warning("Token validation failed: missing user_id (sub)")
            return None
        if token_type != "access":
            logger.warning(f"Token validation failed: invalid token type for user_id={user_id}")
            return None
        logger.debug(f"Token validated successfully for user_id={user_id}")
        return TokenData(user_id=user_id)
    except JWTError:
        logger.warning("Invalid or expired JWT token")
        return None
    except Exception:
        logger.exception("Unexpected error during token verification")
        return None
