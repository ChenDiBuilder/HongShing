from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func

from app.database import AsyncSession, get_db
from app.middleware.auth import require_customer
from app.models import Order, OrderItem, User

router = APIRouter()


class OrderItemRequest(BaseModel):
    menu_item_id: str
    name: str
    price_cents: int
    quantity: int


class CreateOrderRequest(BaseModel):
    items: list[OrderItemRequest]


def _format_order(order: Order, items: list[OrderItem]) -> dict:
    return {
        "id": order.id,
        "subtotal_cents": order.subtotal_cents,
        "discount_cents": order.discount_cents,
        "tax_cents": order.tax_cents,
        "total_cents": order.total_cents,
        "item_count": order.item_count,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "items": [
            {"name": i.name, "price_cents": i.price_cents, "quantity": i.quantity}
            for i in items
        ],
    }


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

    # This direct-create path carries no reward/tax (the money path with reward
    # discounts + tax is /api/cart/checkout); record subtotal == total for parity.
    order = Order(
        user_id=current_user.id,
        subtotal_cents=total_cents,
        discount_cents=0,
        tax_cents=0,
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
        data.append(_format_order(order, items))
    return {"orders": data}


@router.get("/api/customer/me/orders/{order_id}")
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = items_result.scalars().all()
    return {"order": _format_order(order, items)}
