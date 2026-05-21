from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.database import AsyncSession, get_db
from app.models import Order, QRCampaign, Reward, SignupEvent, User
from app.middleware.auth import require_admin

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    # Counts
    total_customers = await db.scalar(
        select(func.count(User.id)).where(User.role == "customer")
    )
    total_campaigns = await db.scalar(
        select(func.count(QRCampaign.id)).where(QRCampaign.active == True)  # noqa: E712
    )
    total_signups = await db.scalar(select(func.count(SignupEvent.id)))
    total_rewards = await db.scalar(select(func.count(Reward.id)))
    issued_rewards = await db.scalar(
        select(func.count(Reward.id)).where(Reward.status == "issued")
    )
    redeemed_rewards = await db.scalar(
        select(func.count(Reward.id)).where(Reward.status == "redeemed")
    )
    total_orders = await db.scalar(select(func.count(Order.id)))
    confirmed_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "confirmed")
    )

    return {
        "data": {
            "total_customers": total_customers or 0,
            "active_campaigns": total_campaigns or 0,
            "total_signups": total_signups or 0,
            "total_rewards": total_rewards or 0,
            "issued_rewards": issued_rewards or 0,
            "redeemed_rewards": redeemed_rewards or 0,
            "total_orders": total_orders or 0,
            "confirmed_orders": confirmed_orders or 0,
        }
    }
