from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.config import settings
from app.db import init_db
from app.logger import logger, setup_logger
from app.routes_orders import router as orders_router
from app.routes_users import router as users_router
from app.routes_wallet import router as wallet_router

setup_logger()

app = FastAPI(
    title="Payment API",
    description="Payment service with JWT auth, users, orders and wallet endpoints",
    version="1.0.0",
)

origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    request_id = uuid4().hex[:10]
    request.state.request_id = request_id
    start = perf_counter()

    response = await call_next(request)

    elapsed = perf_counter() - start
    response.headers["X-Request-Id"] = request_id
    logger.info("%s %s %s %.4fs", request_id, request.method, request.url.path, elapsed)
    return response


@app.on_event("startup")
def startup_event():
    logger.info("Starting service in %s", settings.ENVIRONMENT)
    init_db()


app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")


@app.get("/", tags=["health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Payment API",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api", tags=["meta"])
def api_index():
    return {
        "name": "Payment API",
        "auth": ["/api/auth/register", "/api/auth/login"],
        "users": ["/api/users", "/api/users/{user_id}"],
        "orders": ["/api/orders"],
        "wallet": ["/api/wallet/{customer_id}"],
    }
