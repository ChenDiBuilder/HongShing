import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

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
from app.routes.storefront_customers import router as storefront_customers_router
from app.routes.storefront_orders import router as storefront_orders_router
from app.routes.storefront_reservations import router as storefront_reservations_router
from app.routes.admin_devices import router as admin_devices_router
from app.routes.admin_reservation_slots import router as admin_reservation_slots_router
from app.routes.admin_orders import router as admin_orders_router
from app.routes.admin_analytics import router as admin_analytics_router
from app.routes.admin_insights import router as admin_insights_router
from app.routes.admin_seed import router as admin_seed_router
from app.routes.reservations import router as reservations_router
from app.routes.cart import router as cart_router


def _assert_prod_safety() -> None:
    """Fail fast at startup if production is running with insecure dev defaults."""
    if settings.app_env != "production":
        return
    problems = []
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


def _known_revision_ids() -> set[str]:
    """All revision ids present in the migration scripts."""
    from alembic.script import ScriptDirectory

    return {rev.revision for rev in ScriptDirectory.from_config(_alembic_config()).walk_revisions()}


def _alembic_stamp_head() -> None:
    """Overwrite the version table with head, purging any stale/orphan entry."""
    from alembic import command

    command.stamp(_alembic_config(), "head", purge=True)


async def _recover_orphan_alembic_version(orphans: list[str]) -> None:
    """Heal — or fail loudly on — an alembic_version that points at a revision no
    longer present in the migration scripts (history squashed/rewritten).

    Left unhandled, `upgrade head` fails deep in Alembic with "Can't locate
    revision" and uvicorn never binds — a silent wedge that reads as a hang.
    Production never auto-repairs real data. In non-production, if the live schema
    already matches the ORM models the marker is merely stale, so we re-stamp to head
    and boot; if the schema also differs, we fail clearly (recreate the local DB)."""
    detail = (
        f"alembic_version points at unknown revision(s) {orphans}: the migration "
        f"history was rewritten but this database still references an old id."
    )
    if settings.app_env == "production":
        raise RuntimeError(
            detail + " Refusing to auto-repair production data — run "
            "`alembic stamp <correct_revision>` for the true schema state."
        )

    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    import app.models  # noqa: F401  (register every table on Base.metadata)
    from app.database import Base

    async with engine.connect() as conn:
        diffs = await conn.run_sync(
            lambda c: compare_metadata(MigrationContext.configure(c), Base.metadata)
        )
    if diffs:
        raise RuntimeError(
            detail + f" The live schema also differs from the models ({len(diffs)} "
            "change(s)); it cannot be safely re-stamped. Recreate the local database "
            "(dropdb/createdb) and restart to rebuild it from migrations."
        )
    log.warning("%s Schema matches the models — re-stamping to head.", detail)
    await asyncio.to_thread(_alembic_stamp_head)


async def _run_migrations() -> None:
    """Bring the schema to Alembic head on startup (single-box self-bootstrap).

    - Fresh database (no schema): `upgrade head` builds everything.
    - Legacy create_all database (schema present, no alembic_version): stamp the
      baseline then upgrade, so post-baseline migrations still apply.
    - Orphan alembic_version (stored revision no longer in the scripts): recover
      instead of wedging (see `_recover_orphan_alembic_version`).
    - Already under Alembic: `upgrade head` applies new migrations.

    Errors are deliberately NOT swallowed — a failed migration must surface."""
    from sqlalchemy import inspect, text

    async with engine.connect() as conn:
        has_schema = await conn.run_sync(lambda c: inspect(c).has_table("users"))
        has_version = await conn.run_sync(lambda c: inspect(c).has_table("alembic_version"))
        stored_revs: list[str] = []
        if has_version:
            stored_revs = list(
                (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalars()
            )

    if has_schema and not has_version:
        log.info("Existing schema without alembic_version — adopting (stamp baseline + upgrade).")
        await asyncio.to_thread(_alembic_adopt_legacy)
        return

    if stored_revs:
        known = await asyncio.to_thread(_known_revision_ids)
        orphans = [r for r in stored_revs if r not in known]
        if orphans:
            await _recover_orphan_alembic_version(orphans)
            return

    await asyncio.to_thread(_alembic_upgrade_head)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_prod_safety()
    await _run_migrations()

    from app.services.sms_service import _check_sms_capability

    _check_sms_capability()

    # Starlette never runs a mounted sub-app's lifespan, so the MCP session
    # manager must be driven from here or every /mcp request 500s.
    from app.mcp_server import mcp_lifespan

    async with mcp_lifespan():
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

# Per-box default is "" (nginx serves at the host root); only a legacy path-prefixed
# host sets DEMO_PREFIX. The middleware is a no-op when empty (PRD-12 / SCRUM-77).
DEMO_PREFIX = settings.demo_prefix


@app.middleware("http")
async def strip_demo_prefix(request: Request, call_next):
    if DEMO_PREFIX and request.url.path.startswith(DEMO_PREFIX):
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
app.include_router(storefront_customers_router)
app.include_router(storefront_orders_router)
app.include_router(storefront_reservations_router)

# Admin — Devices & Reservation Slots
app.include_router(admin_devices_router)
app.include_router(admin_reservation_slots_router)
app.include_router(admin_orders_router, prefix="/api/admin", tags=["admin-orders"])
app.include_router(admin_analytics_router, prefix="/api/admin", tags=["admin-analytics"])
app.include_router(admin_insights_router, prefix="/api/admin", tags=["admin-insights"])
app.include_router(admin_seed_router, prefix="/api/admin", tags=["admin-seed"])

# Reservations (customer)
app.include_router(reservations_router)

# Cart (customer)
app.include_router(cart_router)

# Agent tool surface (Act 2): the restaurant as an MCP server. Token-gated;
# 404s when MCP_SERVICE_TOKEN is unset.
from app.mcp_server import build_mcp_asgi  # noqa: E402

app.mount("/mcp", build_mcp_asgi())


_HEALTH_DB_TIMEOUT_S = 2.0


@app.get("/api/health")
async def health(response: Response):
    """Liveness + DB reachability (SCRUM-220).

    Returns 503 when the database is unreachable — the Route53 canary in
    bridgeway-portal/ops/uptime.tf alarms on any non-2xx, so a DB-down pilot
    outage pages instead of hiding behind a hardcoded 200 while every real
    endpoint 500s.
    """
    try:
        async with asyncio.timeout(_HEALTH_DB_TIMEOUT_S):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "db_unreachable"}
    return {"status": "ok"}
