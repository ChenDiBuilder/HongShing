from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.models import QRCampaign, RestaurantSettings
from app.schemas.common import APIResponse, CampaignConfig, LandingConfigResponse

router = APIRouter()


@router.get("/landing-config", response_model=LandingConfigResponse)
async def landing_config(source: str | None = None, db: AsyncSession = Depends(get_db)):
    # Get restaurant settings
    result = await db.execute(select(RestaurantSettings))
    settings = result.scalar_one_or_none()

    if not settings:
        # Return defaults if no settings row exists
        return LandingConfigResponse(
            restaurant_name="Restaurant",
            primary_color="#C41E3A",
            allow_order_without_signup=True,
        )

    # Get campaign if source present
    campaign = None
    if source:
        result = await db.execute(
            select(QRCampaign).where(
                QRCampaign.source_code == source,
                QRCampaign.active == True,  # noqa: E712
            )
        )
        campaign_row = result.scalar_one_or_none()
        if campaign_row:
            campaign = CampaignConfig(
                id=campaign_row.id,
                source_code=campaign_row.source_code,
                landing_headline=campaign_row.landing_headline,
                landing_subtitle=campaign_row.landing_subtitle,
                reward_template_id=campaign_row.reward_template_id,
            )

    return LandingConfigResponse(
        restaurant_name=settings.restaurant_name,
        primary_color=settings.primary_color,
        secondary_color=settings.secondary_color,
        logo_url=settings.logo_url,
        campaign=campaign,
        allow_order_without_signup=settings.allow_order_without_signup,
        external_ordering_url=settings.external_ordering_url,
        support_phone=settings.support_phone,
        privacy_contact_email=settings.privacy_contact_email,
    )


@router.get("/privacy")
async def privacy_page(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RestaurantSettings))
    settings = result.scalar_one_or_none()
    name = settings.restaurant_name if settings else "This restaurant"
    content = (
        f"{name} collects your phone number to provide rewards and order updates. "
        "We do not sell your data to third parties."
    )
    contact = settings.privacy_contact_email if settings else None
    if contact:
        content += f" For questions, contact {contact}."
    return {"title": "Privacy Policy", "content": content}
