"""Admin orders routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import Order, User

router = APIRouter()


@router.get("/orders")
async def list_orders(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    query = select(Order)
    if status:
        query = query.where(Order.status == status)
    query = query.order_by(Order.created_at.desc())

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(offset).limit(limit))
    orders = result.scalars().all()

    return {
        "data": {
            "items": [
                {
                    "id": o.id,
                    "user_id": o.user_id,
                    "total_cents": o.total_cents,
                    "item_count": o.item_count,
                    "status": o.status,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }
