from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.auth import router as auth_router
from app.routes_users import router as users_router
from app.routes_orders import router as orders_router
from app.routes_wallet import router as wallet_router

app = FastAPI(
    title="Payment API",
    description="Production-ready API with JWT Authentication",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
def startup_event():
    init_db()
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")

@app.get("/", tags=["health"])
def health_check():
    return {"status": "healthy", "service": "Payment API"}

@app.get("/api", tags=["info"])
def api_info():
    return {
        "docs": "/docs",
        "auth": {
            "register": "POST /api/auth/register",
            "login": "POST /api/auth/login",
            "protected_routes": "Add header: Authorization: Bearer <token>"
        }
    }