"""Reward template and reward admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import Reward, RewardTemplate, User

router = APIRouter()


class CreateTemplateRequest(BaseModel):
    name: str
    reward_type: str = "fixed"
    reward_value: int = 500
    valid_days: int = 30


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
    body: CreateTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    template = RewardTemplate(
        name=body.name,
        code_prefix="HS",
        reward_type=body.reward_type,
        reward_value=body.reward_value,
        valid_days=body.valid_days,
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


@router.delete("/reward-templates/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(select(RewardTemplate).where(RewardTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Not found")
    template.active = False
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
    from datetime import datetime, timezone

    # Atomic conditional redemption: only the first concurrent request that still
    # sees status='issued' flips it, so a reward can't be double-redeemed.
    result = await db.execute(
        update(Reward)
        .where(Reward.id == reward_id, Reward.status == "issued")
        .values(
            status="redeemed",
            redeemed_at=datetime.now(timezone.utc),
            redemption_source="manual",
        )
    )
    if result.rowcount == 0:
        existing = (
            await db.execute(select(Reward).where(Reward.id == reward_id))
        ).scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail="Reward not found")
        raise HTTPException(status_code=400, detail=f"Reward is {existing.status}")
    await db.commit()
    return {"ok": True}
