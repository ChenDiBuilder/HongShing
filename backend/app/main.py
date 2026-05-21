from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()
from app.database import engine
from app.models import Base
from app.routes import (
    admin,
    admin_auth,
    admin_customers,
    admin_qr,
    admin_rewards,
    admin_settings,
    auth,
    customer,
    public,
    redirects,
    tracking,
)
from app.routes.test_routes import router as test_router
from app.routes.menu import router as menu_router
from app.routes.orders import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass
    yield
    await engine.dispose()


app = FastAPI(
    title="HongShing API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin_auth.router, prefix="/api/admin/auth", tags=["admin-auth"])

# Public
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(redirects.router, prefix="/api/redirects", tags=["redirects"])
app.include_router(tracking.router, prefix="/api", tags=["tracking"])

# Customer (authenticated)
app.include_router(customer.router, prefix="/api", tags=["customer"])

# Admin
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_qr.router, prefix="/api/admin", tags=["admin-qr"])
app.include_router(admin_rewards.router, prefix="/api/admin", tags=["admin-rewards"])
app.include_router(admin_customers.router, prefix="/api/admin", tags=["admin-customers"])
app.include_router(admin_settings.router, prefix="/api/admin", tags=["admin-settings"])

# Test
app.include_router(test_router)

# Menu
app.include_router(menu_router)

# Orders
app.include_router(orders_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
