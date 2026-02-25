import time
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.logger import logger, setup_logger
from app.db import init_db
from app.auth import router as auth_router
from app.routes_users import router as users_router
from app.routes_orders import router as orders_router
from app.routes_wallet import router as wallet_router
from app.config import settings
# Initialize logging first
setup_logger()
app = FastAPI(
    title="Payment API",
    description="Production-ready API with JWT Authentication",
    version="1.0.0"
)
# CORS - restrict in production
allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if settings.ENVIRONMENT != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Request logging middleware with correlation ID
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    client = request.client.host if request.client else "unknown"
    logger.info(f"[{request_id}] START {request.method} {request.url.path} from {client}")
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"[{request_id}] END {response.status_code} in {duration:.3f}s")
        return response
    except HTTPException as e:
        duration = time.time() - start_time
        logger.warning(f"[{request_id}] END {e.status_code} in {duration:.3f}s: {e.detail}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[{request_id}] ERROR after {duration:.3f}s: {type(e).__name__}", exc_info=True)
        raise
@app.on_event("startup")
def startup_event():
    logger.info(f"Starting Payment API in {settings.ENVIRONMENT} environment")
    init_db()
    logger.info("Database initialized")
# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")
@app.get("/", tags=["health"])
def health_check():
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "service": "Payment API",
        "environment": settings.ENVIRONMENT
    }