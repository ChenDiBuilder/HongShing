from app.routes.auth import router as auth_router
from app.routes.public import router as public_router
from app.routes.admin import router as admin_router
from app.routes.admin_auth import router as admin_auth_router
from app.routes.customer import router as customer_router
from app.routes.admin_qr import router as admin_qr_router
from app.routes.admin_rewards import router as admin_rewards_router
from app.routes.admin_customers import router as admin_customers_router
from app.routes.admin_settings import router as admin_settings_router
from app.routes.tracking import router as tracking_router
from app.routes.redirects import router as redirects_router

__all__ = [
    "auth_router",
    "public_router",
    "admin_router",
    "admin_auth_router",
    "customer_router",
    "admin_qr_router",
    "admin_rewards_router",
    "admin_customers_router",
    "admin_settings_router",
    "tracking_router",
    "redirects_router",
]
