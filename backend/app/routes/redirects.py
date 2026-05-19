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

    # Log anonymous redirect
    redirect_event = ExternalOrderRedirect(
        destination_url=url or "https://hongshing.ca/order",
        provider=settings.external_ordering_provider if settings else None,
    )
    db.add(redirect_event)
    await db.commit()

    return {"destination_url": url or "https://hongshing.ca/order"}
