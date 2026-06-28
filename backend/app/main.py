import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()
from app.database import engine
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


log = logging.getLogger("uvicorn.error")


def _alembic_config():
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parent.parent  # app/ -> backend/
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    return cfg


def _alembic_upgrade_head() -> None:
    """Apply all pending migrations (blocking; run in a worker thread)."""
    from alembic import command

    command.upgrade(_alembic_config(), "head")


def _alembic_adopt_legacy() -> None:
    """Adopt a create_all-built database into Alembic without re-creating it.

    The legacy schema matches the Alembic BASELINE, so we stamp the baseline
    revision (NOT head — that would skip any post-baseline migrations) and then
    upgrade, which applies everything created after the baseline (e.g. the
    uniqueness-index migration)."""
    from alembic import command
    from alembic.script import ScriptDirectory

    cfg = _alembic_config()
    base_rev = ScriptDirectory.from_config(cfg).get_base()
    command.stamp(cfg, base_rev)
    command.upgrade(cfg, "head")


async def _run_migrations() -> None:
    """Bring the schema to Alembic head on startup (single-box self-bootstrap).

    - Fresh database (no schema): `upgrade head` builds everything.
    - Legacy create_all database (schema present, no alembic_version): stamp the
      baseline then upgrade, so post-baseline migrations still apply.
    - Already under Alembic: `upgrade head` applies new migrations.

    Errors are deliberately NOT swallowed — a failed migration must surface."""
    from sqlalchemy import inspect

    async with engine.connect() as conn:
        has_schema = await conn.run_sync(lambda c: inspect(c).has_table("users"))
        has_version = await conn.run_sync(lambda c: inspect(c).has_table("alembic_version"))

    if has_schema and not has_version:
        log.info("Existing schema without alembic_version — adopting (stamp baseline + upgrade).")
        await asyncio.to_thread(_alembic_adopt_legacy)
    else:
        await asyncio.to_thread(_alembic_upgrade_head)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_prod_safety()
    await _run_migrations()

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
