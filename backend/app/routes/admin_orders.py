"""Admin orders routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import Order, OrderItem, User

router = APIRouter()


@router.get("/orders")
async def list_orders(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    query = select(Order).options(selectinload(Order.user))
    if status:
        query = query.where(Order.status == status)
    query = query.order_by(Order.created_at.desc())

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    orders_result = await db.execute(query.offset(offset).limit(limit))
    orders = orders_result.unique().scalars().all()

    order_ids = [o.id for o in orders]
    items_map: dict[str, list[dict]] = {}
    if order_ids:
        items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id.in_(order_ids))
        )
        for item in items_result.scalars().all():
            items_map.setdefault(item.order_id, []).append(
                {
                    "name": item.name,
                    "price_cents": item.price_cents,
                    "quantity": item.quantity,
                }
            )

    return {
        "data": {
            "items": [
                {
                    "id": o.id,
                    "user_id": o.user_id,
                    "user_phone": o.user.phone if o.user else None,
                    "total_cents": o.total_cents,
                    "item_count": o.item_count,
                    "status": o.status,
                    "items": items_map.get(o.id, []),
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.user)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = items_result.scalars().all()

    return {
        "data": {
            "id": order.id,
            "user_id": order.user_id,
            "user_phone": order.user.phone if order.user else None,
            "user_name": order.user.name if order.user else None,
            "total_cents": order.total_cents,
            "item_count": order.item_count,
            "status": order.status,
            "items": [
                {
                    "name": i.name,
                    "price_cents": i.price_cents,
                    "quantity": i.quantity,
                }
                for i in items
            ],
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }
    }
