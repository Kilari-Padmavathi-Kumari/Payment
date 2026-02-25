from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = Field(
        default="Payment API",
        validation_alias=AliasChoices("APP_NAME", "app_name"),
    )

    enable_strict_idempotency_check: bool = False
    transaction_settlement_window: float = 0.0
    enable_graceful_degradation: bool = False
    wallet_operation_lock_timeout: int = 0

    ENVIRONMENT: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV", "environment", "app_env"),
    )
    ALLOWED_ORIGINS: str = "*"


settings = Settings()
