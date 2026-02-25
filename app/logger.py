import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config import settings
# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)
def setup_logger(name: str = "payment_api") -> logging.Logger:
    """Configure production-ready logger"""
    log_level = getattr(logging, getattr(settings, 'LOG_LEVEL', 'INFO').upper(), logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    # Prevent duplicate handlers on reload
    if logger.handlers:
        return logger
    # Structured format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Console handler (for docker/monitoring)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    # Rotating file handler (for production persistence)
    file_handler = RotatingFileHandler(
        filename=LOGS_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB per file
        backupCount=5,  # Keep 5 old files
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Reduce noise from dependencies
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)

    return logger
# Export default logger instance
logger = setup_logger()
