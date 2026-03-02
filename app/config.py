from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL", "database_url"))
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
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

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str):
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        value_upper = value.upper()
        if value_upper not in allowed:
            return "INFO"
        return value_upper

    @property
    def allowed_origins_list(self):
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
