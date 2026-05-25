"""QR campaign admin CRUD routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import QRCampaign, User

router = APIRouter()


class CreateCampaignRequest(BaseModel):
    name: str
    source_code: str
    landing_headline: str | None = None
    landing_subtitle: str | None = None
    reward_template_id: str | None = None


@router.get("/qr-campaigns")
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(select(QRCampaign).order_by(QRCampaign.created_at.desc()))
    campaigns = result.scalars().all()
    return {
        "data": [
            {
                "id": c.id,
                "name": c.name,
                "source_code": c.source_code,
                "landing_headline": c.landing_headline,
                "landing_subtitle": c.landing_subtitle,
                "active": c.active,
                "created_at": c.created_at.isoformat(),
            }
            for c in campaigns
        ]
    }


@router.post("/qr-campaigns")
async def create_campaign(
    body: CreateCampaignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    campaign = QRCampaign(
        name=body.name,
        source_code=body.source_code,
        landing_headline=body.landing_headline,
        landing_subtitle=body.landing_subtitle,
        reward_template_id=body.reward_template_id,
        created_by=current_user.id,
        active=True,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"data": {"id": campaign.id, "name": campaign.name, "source_code": campaign.source_code}}


@router.patch("/qr-campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    name: str | None = None,
    description: str | None = None,
    landing_headline: str | None = None,
    landing_subtitle: str | None = None,
    active: bool | None = None,
    reward_template_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(select(QRCampaign).where(QRCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if name is not None:
        campaign.name = name
    if description is not None:
        campaign.description = description
    if landing_headline is not None:
        campaign.landing_headline = landing_headline
    if landing_subtitle is not None:
        campaign.landing_subtitle = landing_subtitle
    if active is not None:
        campaign.active = active
    if reward_template_id is not None:
        campaign.reward_template_id = reward_template_id
    await db.commit()
    return {"ok": True}
