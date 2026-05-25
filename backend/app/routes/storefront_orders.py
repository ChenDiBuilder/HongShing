from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_device
from app.models import Device, Order, OrderItem, OrderStatusEvent, User

router = APIRouter(prefix="/api/storefront", tags=["storefront"])


@router.get("/orders")
async def list_orders(
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device),
):
    active_statuses = ["confirmed", "preparing", "ready"]
    result = await db.execute(
        select(Order)
        .where(Order.status.in_(active_statuses))
        .order_by(Order.created_at.asc())
        .limit(50)
    )
    orders = result.scalars().all()

    data = []
    for order in orders:
        items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = items_result.scalars().all()
        user_result = await db.execute(
            select(User.phone, User.name).where(User.id == order.user_id)
        )
        user = user_result.first()
        data.append(
            {
                "id": order.id,
                "total_cents": order.total_cents,
                "item_count": order.item_count,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "customer_phone": user[0] if user else None,
                "customer_name": user[1] if user else None,
                "items": [
                    {
                        "name": i.name,
                        "price_cents": i.price_cents,
                        "quantity": i.quantity,
                    }
                    for i in items
                ],
            }
        )
    return {"orders": data}


class UpdateStatusRequest(BaseModel):
    status: str
    notes: str | None = None


VALID_TRANSITIONS = {
    "confirmed": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["picked_up", "cancelled"],
    "picked_up": [],
    "cancelled": [],
}


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    body: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    valid_transitions = VALID_TRANSITIONS.get(order.status, [])
    if body.status not in valid_transitions:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{order.status}' to '{body.status}'",
        )

    event = OrderStatusEvent(
        order_id=order.id,
        device_id=device.id,
        previous_status=order.status,
        new_status=body.status,
        notes=body.notes,
    )
    db.add(event)
    order.status = body.status
    await db.commit()

    return {"order_id": order.id, "status": order.status}
