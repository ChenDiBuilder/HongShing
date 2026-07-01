import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.models import QRCampaign, RestaurantSettings
from app.schemas.common import APIResponse, CampaignConfig, LandingConfigResponse
from app.services.hours import compute_open_status

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

    hours_display = None
    if settings.hours_json:
        try:
            parsed = json.loads(settings.hours_json)
            if isinstance(parsed, dict):
                hours_display = {str(k): str(v) for k, v in parsed.items()}
        except (ValueError, TypeError):
            hours_display = None

    languages = None
    if settings.languages:
        langs = [s.strip() for s in settings.languages.split(",") if s.strip()]
        languages = langs or None

    # Open/closed is computed server-side in the restaurant's timezone so the SPA's
    # "currently closed" banner tracks real operating hours even while the box is
    # up (it starts ~30m before open, stops ~15m before close).
    is_open, hours_today = compute_open_status(hours_display, settings.timezone)

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
        address=settings.address,
        contact_phone=settings.contact_phone,
        hours_display=hours_display,
        is_open=is_open,
        hours_today=hours_today,
        pickup_estimate=settings.pickup_estimate,
        tax_rate=settings.tax_rate,
        currency_symbol=settings.currency_symbol,
        tagline=settings.tagline,
        reward_success_copy=settings.reward_success_copy,
        legal_name=settings.legal_name,
        languages=languages,
        storefront_enabled=settings.storefront_enabled,
    )


@router.get("/privacy")
async def privacy_page(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RestaurantSettings))
    settings = result.scalar_one_or_none()
    # Prefer the registered legal name in the privacy notice; fall back to the
    # display name, then a neutral placeholder (PRD-12 S9 / SCRUM-66).
    name = "This restaurant"
    if settings:
        name = settings.legal_name or settings.restaurant_name
    content = (
        f"{name} collects your phone number to provide rewards and order updates. "
        "We do not sell your data to third parties."
    )
    contact = settings.privacy_contact_email if settings else None
    if contact:
        content += f" For questions, contact {contact}."
    return {"title": "Privacy Policy", "content": content}
