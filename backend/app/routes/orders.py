from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func

from app.database import AsyncSession, get_db
from app.middleware.auth import require_customer
from app.models import Order, OrderItem, User
from app.models.menu import MenuItem

router = APIRouter()


class OrderItemRequest(BaseModel):
    menu_item_id: str
    name: str
    price_cents: int
    quantity: int


class CreateOrderRequest(BaseModel):
    items: list[OrderItemRequest]


@router.post("/api/orders")
async def create_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    if not body.items:
        raise HTTPException(status_code=400, detail="No items in order")

    total_cents = sum(i.price_cents * i.quantity for i in body.items)
    item_count = sum(i.quantity for i in body.items)

    order = Order(
        user_id=current_user.id,
        total_cents=total_cents,
        item_count=item_count,
        status="confirmed",
    )
    db.add(order)
    await db.flush()

    for item in body.items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item.menu_item_id,
            name=item.name,
            price_cents=item.price_cents,
            quantity=item.quantity,
        )
        db.add(order_item)

    await db.commit()

    return {
        "order_id": order.id,
        "total_cents": order.total_cents,
        "item_count": order.item_count,
        "status": order.status,
    }


@router.get("/api/customer/me/orders")
async def my_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(20)
    )
    orders = result.scalars().all()

    data = []
    for order in orders:
        items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = items_result.scalars().all()
        data.append(
            {
                "id": order.id,
                "total_cents": order.total_cents,
                "item_count": order.item_count,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
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
