"""Customer admin routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import (
    ExternalOrderRedirect,
    Order,
    Reward,
    SignupEvent,
    User,
    UserNotificationPreference,
)

router = APIRouter()


@router.get("/customers")
async def list_customers(
    search: str | None = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    # Per-customer value signals in one aggregate join (no N+1): visits,
    # average ticket, most recent order. Cancelled orders don't count.
    stats = (
        select(
            Order.user_id.label("uid"),
            func.count(Order.id).label("visits"),
            func.avg(Order.total_cents).label("avg_cents"),
            func.max(Order.created_at).label("last_order_at"),
        )
        .where(Order.status != "cancelled")
        .group_by(Order.user_id)
        .subquery()
    )

    query = (
        select(User, stats.c.visits, stats.c.avg_cents, stats.c.last_order_at)
        .join(stats, stats.c.uid == User.id, isouter=True)
        .where(User.role == "customer")
    )

    if search:
        query = query.where(
            or_(
                User.phone.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%"),
            )
        )

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(
        query.order_by(stats.c.last_order_at.desc().nullslast(), User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()

    return {
        "data": {
            "items": [
                {
                    "id": c.id,
                    "phone": c.phone,
                    "name": c.name,
                    "email": c.email,
                    "created_at": c.created_at.isoformat(),
                    "visits": visits or 0,
                    "avg_ticket_cents": int(avg_cents) if avg_cents is not None else None,
                    "last_order_at": last_order_at.isoformat() if last_order_at else None,
                }
                for c, visits, avg_cents, last_order_at in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(
        select(User).where(User.id == customer_id, User.role == "customer")
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Rewards
    result = await db.execute(
        select(Reward).where(Reward.user_id == customer_id).order_by(Reward.issued_at.desc())
    )
    rewards = result.scalars().all()

    # Orders
    result = await db.execute(
        select(Order).where(Order.user_id == customer_id).order_by(Order.created_at.desc()).limit(20)
    )
    orders = result.scalars().all()

    # Redirects
    result = await db.execute(
        select(ExternalOrderRedirect)
        .where(ExternalOrderRedirect.user_id == customer_id)
        .order_by(ExternalOrderRedirect.created_at.desc())
        .limit(10)
    )
    redirects = result.scalars().all()

    # Consent
    result = await db.execute(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == customer_id
        )
    )
    consent = result.scalar_one_or_none()

    return {
        "data": {
            "id": customer.id,
            "phone": customer.phone,
            "name": customer.name,
            "email": customer.email,
            "created_at": customer.created_at.isoformat(),
            "rewards": [
                {
                    "id": r.id,
                    "code": r.code,
                    "status": r.status,
                    "issued_at": r.issued_at.isoformat(),
                }
                for r in rewards
            ],
            "orders": [
                {
                    "id": o.id,
                    "total_cents": o.total_cents,
                    "item_count": o.item_count,
                    "status": o.status,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
            "redirects": [
                {
                    "id": r.id,
                    "destination_url": r.destination_url,
                    "created_at": r.created_at.isoformat(),
                }
                for r in redirects
            ],
            "consent": {
                "sms_marketing_opt_in": consent.sms_marketing_opt_in if consent else False,
                "sms_transactional_enabled": consent.sms_transactional_enabled if consent else True,
            }
            if consent
            else None,
        }
    }


@router.patch("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(select(User).where(User.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    await db.commit()
    return {"ok": True}
