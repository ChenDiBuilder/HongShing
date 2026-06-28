"""Miscellaneous public routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.models import ExternalOrderRedirect, RestaurantSettings

router = APIRouter()


@router.get("/external-order")
async def external_order_redirect(db: AsyncSession = Depends(get_db)):
    """Serve the external ordering URL (for the 'Order without reward' flow)."""
    result = await db.execute(select(RestaurantSettings))
    settings = result.scalar_one_or_none()

    url = settings.external_ordering_url if settings else None

    # Only log a redirect when a destination is actually configured — never fall
    # back to a hardcoded HongShing URL (a clone must not send customers to
    # hongshing.ca). An unset URL returns null; the SPA shows an empty state.
    if url:
        db.add(
            ExternalOrderRedirect(
                destination_url=url,
                provider=settings.external_ordering_provider if settings else None,
            )
        )
        await db.commit()

    return {"destination_url": url}
