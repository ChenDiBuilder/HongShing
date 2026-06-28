from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

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
from app.routes.menu import router as menu_router
from app.routes.orders import router as orders_router
from app.routes.storefront_auth import router as storefront_auth_router
from app.routes.storefront_orders import router as storefront_orders_router
from app.routes.storefront_reservations import router as storefront_reservations_router
from app.routes.admin_devices import router as admin_devices_router
from app.routes.admin_reservation_slots import router as admin_reservation_slots_router
from app.routes.admin_orders import router as admin_orders_router
from app.routes.admin_analytics import router as admin_analytics_router
from app.routes.admin_seed import router as admin_seed_router
from app.routes.reservations import router as reservations_router
from app.routes.cart import router as cart_router


def _assert_prod_safety() -> None:
    """Fail fast at startup if production is running with insecure dev defaults."""
    if settings.app_env != "production":
        return
    problems = []
    if settings.hardcoded_otp:
        problems.append('HARDCODED_OTP must be empty in production (set HARDCODED_OTP="")')
    if settings.secret_key == "change-me-in-production":
        problems.append("SECRET_KEY is still the insecure default")
    if settings.otp_pepper == "change-me-in-production":
        problems.append("OTP_PEPPER is still the insecure default")
    if problems:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration: "
            + "; ".join(problems)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_prod_safety()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS tags text[]"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS popular boolean DEFAULT false"))
            except Exception:
                pass
    except Exception:
        pass

    from app.services.sms_service import _check_sms_capability

    _check_sms_capability()

    yield
    await engine.dispose()


app = FastAPI(
    title="Restaurant Platform API",
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

DEMO_PREFIX = "/product-demo/hongshing"


@app.middleware("http")
async def strip_demo_prefix(request: Request, call_next):
    if request.url.path.startswith(DEMO_PREFIX):
        request.scope["path"] = request.url.path[len(DEMO_PREFIX):]
        request.scope["root_path"] = DEMO_PREFIX
    return await call_next(request)

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

# Menu
app.include_router(menu_router)

# Orders
app.include_router(orders_router)

# Storefront
app.include_router(storefront_auth_router)
app.include_router(storefront_orders_router)
app.include_router(storefront_reservations_router)

# Admin — Devices & Reservation Slots
app.include_router(admin_devices_router)
app.include_router(admin_reservation_slots_router)
app.include_router(admin_orders_router, prefix="/api/admin", tags=["admin-orders"])
app.include_router(admin_analytics_router, prefix="/api/admin", tags=["admin-analytics"])
app.include_router(admin_seed_router, prefix="/api/admin", tags=["admin-seed"])

# Reservations (customer)
app.include_router(reservations_router)

# Cart (customer)
app.include_router(cart_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
