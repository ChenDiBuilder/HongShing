from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_customer
from app.models import Cart, CartItem, User
from app.models.menu import MenuItem

router = APIRouter(prefix="/api", tags=["cart"])


class AddToCartRequest(BaseModel):
    menu_item_id: str
    name: str
    price_cents: int
    quantity: int = 1


class UpdateQuantityRequest(BaseModel):
    quantity: int


@router.get("/cart")
async def get_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id, Cart.is_active == True)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        return {"cart": {"items": [], "subtotal_cents": 0, "item_count": 0}}

    items_result = await db.execute(
        select(CartItem, MenuItem.image_url)
        .outerjoin(MenuItem, CartItem.menu_item_id == MenuItem.id)
        .where(CartItem.cart_id == cart.id)
    )
    items = items_result.all()

    subtotal = sum(i[0].price_cents * i[0].quantity for i in items)
    count = sum(i[0].quantity for i in items)

    return {
        "cart": {
            "id": cart.id,
            "items": [
                {
                    "id": item.id,
                    "menu_item_id": item.menu_item_id,
                    "name": item.name,
                    "price_cents": item.price_cents,
                    "image_url": img_url,
                    "quantity": item.quantity,
                }
                for item, img_url in items
            ],
            "subtotal_cents": subtotal,
            "item_count": count,
        }
    }


@router.post("/cart/items")
async def add_to_cart(
    body: AddToCartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id, Cart.is_active == True)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        await db.flush()

    # Check if item already in cart
    existing = await db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.menu_item_id == body.menu_item_id
        )
    )
    item = existing.scalar_one_or_none()
    if item:
        item.quantity += body.quantity
    else:
        item = CartItem(
            cart_id=cart.id,
            menu_item_id=body.menu_item_id,
            name=body.name,
            price_cents=body.price_cents,
            quantity=body.quantity,
        )
        db.add(item)

    await db.commit()
    return {"ok": True}


@router.patch("/cart/items/{item_id}")
async def update_cart_item(
    item_id: str,
    body: UpdateQuantityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(select(CartItem).where(CartItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if body.quantity <= 0:
        await db.delete(item)
    else:
        item.quantity = body.quantity
    await db.commit()
    return {"ok": True}


@router.delete("/cart/items/{item_id}")
async def remove_from_cart(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(select(CartItem).where(CartItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"ok": True}


@router.delete("/cart")
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id, Cart.is_active == True)
    )
    cart = result.scalar_one_or_none()
    if cart:
        cart.is_active = False
        await db.commit()
    return {"ok": True}


@router.post("/cart/checkout")
async def checkout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id, Cart.is_active == True)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    items_result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )
    items = items_result.scalars().all()

    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Create order from cart
    from app.models.order import Order as OrderModel
    from app.models.order import OrderItem as OrderItemModel

    total_cents = sum(i.price_cents * i.quantity for i in items)
    item_count = sum(i.quantity for i in items)

    order = OrderModel(
        user_id=current_user.id,
        total_cents=total_cents,
        item_count=item_count,
        status="confirmed",
    )
    db.add(order)
    await db.flush()

    for item in items:
        order_item = OrderItemModel(
            order_id=order.id,
            menu_item_id=item.menu_item_id,
            name=item.name,
            price_cents=item.price_cents,
            quantity=item.quantity,
        )
        db.add(order_item)

    # Deactivate cart
    cart.is_active = False
    await db.commit()

    return {
        "order_id": order.id,
        "total_cents": order.total_cents,
        "item_count": order.item_count,
        "status": order.status,
    }
