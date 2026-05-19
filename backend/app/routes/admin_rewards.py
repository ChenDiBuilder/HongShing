"""Reward template and reward admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import Reward, RewardTemplate, User

router = APIRouter()


# --- Reward Templates ---

@router.get("/reward-templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(select(RewardTemplate).order_by(RewardTemplate.created_at.desc()))
    templates = result.scalars().all()
    return {
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "code_prefix": t.code_prefix,
                "reward_type": t.reward_type,
                "reward_value": t.reward_value,
                "min_order_cents": t.min_order_cents,
                "valid_days": t.valid_days,
                "max_uses_per_user": t.max_uses_per_user,
                "active": t.active,
            }
            for t in templates
        ]
    }


@router.post("/reward-templates")
async def create_template(
    name: str,
    reward_type: str = "fixed",
    reward_value: int = 500,
    valid_days: int = 30,
    min_order_cents: int | None = None,
    max_uses_per_user: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    template = RewardTemplate(
        name=name,
        code_prefix="HS",
        reward_type=reward_type,
        reward_value=reward_value,
        valid_days=valid_days,
        min_order_cents=min_order_cents,
        max_uses_per_user=max_uses_per_user,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return {"data": {"id": template.id, "name": template.name}}


@router.patch("/reward-templates/{template_id}")
async def update_template(
    template_id: str,
    name: str | None = None,
    reward_type: str | None = None,
    reward_value: int | None = None,
    valid_days: int | None = None,
    active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(select(RewardTemplate).where(RewardTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Not found")
    if name is not None:
        template.name = name
    if reward_type is not None:
        template.reward_type = reward_type
    if reward_value is not None:
        template.reward_value = reward_value
    if valid_days is not None:
        template.valid_days = valid_days
    if active is not None:
        template.active = active
    await db.commit()
    return {"ok": True}


# --- Issued Rewards ---

@router.get("/rewards")
async def list_rewards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(
        select(Reward).order_by(Reward.issued_at.desc()).limit(100)
    )
    rewards = result.scalars().all()
    return {
        "data": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "code": r.code,
                "status": r.status,
                "source_code": r.source_code,
                "issued_at": r.issued_at.isoformat(),
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "redeemed_at": r.redeemed_at.isoformat() if r.redeemed_at else None,
                "redemption_source": r.redemption_source,
            }
            for r in rewards
        ]
    }


@router.patch("/rewards/{reward_id}/redeem")
async def redeem_reward(
    reward_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    if reward.status != "issued":
        raise HTTPException(status_code=400, detail=f"Reward is {reward.status}")

    from datetime import datetime, timezone

    reward.status = "redeemed"
    reward.redeemed_at = datetime.now(timezone.utc)
    reward.redemption_source = "manual"
    await db.commit()
    return {"ok": True}
