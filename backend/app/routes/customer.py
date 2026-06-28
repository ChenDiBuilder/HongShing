"""Customer-facing routes: rewards, profile, redirects."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_customer
from app.models import (
    ExternalOrderRedirect,
    QRCampaign,
    RestaurantSettings,
    Reward,
    RewardTemplate,
    ShortLink,
    User,
)
from app.schemas.common import (
    ClaimRewardRequest,
    ClaimRewardResponse,
    OrderRedirectRequest,
    OrderRedirectResponse,
    RewardResponse,
    UserResponse,
)
from app.services.reward_service import generate_reward_code

router = APIRouter()


@router.get("/customer/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(require_customer),
):
    return UserResponse(
        id=current_user.id,
        phone=current_user.phone,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )


@router.patch("/customer/me")
async def update_profile(
    name: str | None = None,
    email: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    if name is not None:
        current_user.name = name
    if email is not None:
        current_user.email = email
    await db.commit()
    return {"ok": True}


@router.get("/customer/me/rewards")
async def my_rewards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Reward)
        .where(Reward.user_id == current_user.id, Reward.status.in_(["issued", "redeemed"]))
        .order_by(Reward.issued_at.desc())
    )
    rewards = result.scalars().all()
    return {
        "data": [
            {
                "id": r.id,
                "code": r.code,
                "status": r.status,
                "issued_at": r.issued_at.isoformat(),
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rewards
        ]
    }


@router.post("/rewards/claim", response_model=ClaimRewardResponse)
async def claim_reward(
    body: ClaimRewardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    # Determine reward template
    template = None
    if body.campaign_id:
        result = await db.execute(
            select(QRCampaign).where(QRCampaign.id == body.campaign_id, QRCampaign.active == True)  # noqa: E712
        )
        campaign = result.scalar_one_or_none()
        if campaign and campaign.reward_template_id:
            result = await db.execute(
                select(RewardTemplate).where(RewardTemplate.id == campaign.reward_template_id)
            )
            template = result.scalar_one_or_none()

    if not template:
        # Use default template from settings
        result = await db.execute(select(RestaurantSettings))
        settings = result.scalar_one_or_none()
        if settings and settings.default_reward_template_id:
            result = await db.execute(
                select(RewardTemplate).where(RewardTemplate.id == settings.default_reward_template_id)
            )
            template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=400, detail="No active reward available")

    # Check user hasn't already claimed this template
    result = await db.execute(
        select(Reward).where(
            Reward.user_id == current_user.id,
            Reward.reward_template_id == template.id,
            Reward.status == "issued",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return ClaimRewardResponse(
            reward=RewardResponse(
                id=existing.id,
                code=existing.code,
                status=existing.status,
                reward_type=template.reward_type,
                reward_value=template.reward_value,
                issued_at=existing.issued_at,
                expires_at=existing.expires_at,
            ),
            short_link=None,
        )

    # Generate unique code
    code = generate_reward_code()
    for _ in range(5):
        result = await db.execute(select(Reward).where(Reward.code == code))
        if not result.scalar_one_or_none():
            break
        code = generate_reward_code()

    expires_at = datetime.now(timezone.utc) + timedelta(days=template.valid_days)

    reward = Reward(
        user_id=current_user.id,
        reward_template_id=template.id,
        code=code,
        source_code=body.source_code,
        qr_campaign_id=body.campaign_id,
        status="issued",
        expires_at=expires_at,
    )
    db.add(reward)
    await db.flush()

    # Create short link
    short_code = code[3:].lower()
    short_link = ShortLink(
        code=short_code,
        destination_url=f"https://hongshing.ca/r/{code}",
        link_type="reward",
        user_id=current_user.id,
        reward_id=reward.id,
        expires_at=expires_at,
    )
    db.add(short_link)
    await db.commit()
    await db.refresh(reward)

    return ClaimRewardResponse(
        reward=RewardResponse(
            id=reward.id,
            code=reward.code,
            status=reward.status,
            reward_type=template.reward_type,
            reward_value=template.reward_value,
            issued_at=reward.issued_at,
            expires_at=reward.expires_at,
        ),
        short_link=f"https://hongshing.ca/r/{code}",
    )


@router.post("/redirects/order", response_model=OrderRedirectResponse)
async def redirect_to_order(
    body: OrderRedirectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Log a redirect event and return the external ordering URL. No auth required."""

    result = await db.execute(select(RestaurantSettings))
    settings = result.scalar_one_or_none()

    destination = ""
    if settings and settings.external_ordering_url:
        destination = settings.external_ordering_url
        if body.reward_id:
            result = await db.execute(select(Reward).where(Reward.id == body.reward_id))
            reward = result.scalar_one_or_none()
            if reward:
                destination = f"{destination}?promo={reward.code}"

    # No hardcoded HongShing fallback — a clone with no external ordering URL
    # returns an empty destination and the SPA shows an "ordering not set up" state.
    redirect_event = ExternalOrderRedirect(
        user_id=None,
        reward_id=body.reward_id,
        source_code=body.source_code,
        qr_campaign_id=body.campaign_id,
        destination_url=destination,
        provider=settings.external_ordering_provider if settings else None,
    )
    db.add(redirect_event)
    await db.commit()

    return OrderRedirectResponse(destination_url=destination)
