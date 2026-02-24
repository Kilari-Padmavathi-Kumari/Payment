from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Database configuration
    database_url: str = "postgresql+psycopg2://postgres:localhost@localhost:5432/appdb"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "asdfghjkl")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Order processing configuration
    enable_strict_idempotency_check: bool = False
    transaction_settlement_window: float = 0.0
    enable_graceful_degradation: bool = False
    
    # Wallet operation configuration
    wallet_operation_lock_timeout: int = 0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()