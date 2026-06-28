from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSession, get_db
from app.middleware.auth import require_customer
from app.models import Cart, CartItem, RestaurantSettings, Reward, RewardTemplate, User
from app.models.menu import MenuItem
from app.services.reward_service import calculate_discount

router = APIRouter(prefix="/api", tags=["cart"])


class AddToCartRequest(BaseModel):
    menu_item_id: str
    name: str
    price_cents: int
    quantity: int = 1


class UpdateQuantityRequest(BaseModel):
    quantity: int


class CheckoutRequest(BaseModel):
    # Optional reward the customer chose to redeem at checkout (PRD-12 / SCRUM-76).
    reward_id: str | None = None


@router.get("/cart")
async def get_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == current_user.id, Cart.is_active == True)
        .order_by(Cart.created_at.desc())
    )
    # Use the newest active cart and tolerate duplicates: a non-atomic get-or-create
    # in add_to_cart can race two rapid adds into two active carts; scalar_one_or_none
    # would then raise MultipleResultsFound and 500 every checkout for that user.
    cart = result.scalars().first()
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
    # Atomically get-or-create the user's single active cart. The partial unique
    # index uq_carts_one_active_per_user guarantees at most one, so concurrent
    # "add" taps converge on the same cart instead of creating duplicates.
    await db.execute(
        pg_insert(Cart)
        .values(user_id=current_user.id)
        .on_conflict_do_nothing(index_elements=["user_id"], index_where=text("is_active"))
    )
    cart = (
        await db.execute(
            select(Cart)
            .where(Cart.user_id == current_user.id, Cart.is_active == True)  # noqa: E712
            .order_by(Cart.created_at.desc())
        )
    ).scalars().first()

    # Upsert the line item: a concurrent add of the same item merges the quantity
    # (uq_cart_items_cart_menu) rather than creating a duplicate line.
    await db.execute(
        pg_insert(CartItem)
        .values(
            cart_id=cart.id,
            menu_item_id=body.menu_item_id,
            name=body.name,
            price_cents=body.price_cents,
            quantity=body.quantity,
        )
        .on_conflict_do_update(
            index_elements=["cart_id", "menu_item_id"],
            set_={"quantity": CartItem.quantity + body.quantity},
        )
    )
    await db.commit()
    return {"ok": True}


@router.patch("/cart/items/{item_id}")
async def update_cart_item(
    item_id: str,
    body: UpdateQuantityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    # Scope the lookup to the caller's own cart so one customer can't read or
    # mutate another's cart items by guessing an item id (IDOR).
    result = await db.execute(
        select(CartItem)
        .join(Cart, CartItem.cart_id == Cart.id)
        .where(CartItem.id == item_id, Cart.user_id == current_user.id)
    )
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
    # Scope the lookup to the caller's own cart so one customer can't read or
    # mutate another's cart items by guessing an item id (IDOR).
    result = await db.execute(
        select(CartItem)
        .join(Cart, CartItem.cart_id == Cart.id)
        .where(CartItem.id == item_id, Cart.user_id == current_user.id)
    )
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
        select(Cart)
        .where(Cart.user_id == current_user.id, Cart.is_active == True)
        .order_by(Cart.created_at.desc())
    )
    # Use the newest active cart and tolerate duplicates: a non-atomic get-or-create
    # in add_to_cart can race two rapid adds into two active carts; scalar_one_or_none
    # would then raise MultipleResultsFound and 500 every checkout for that user.
    cart = result.scalars().first()
    if cart:
        cart.is_active = False
        await db.commit()
    return {"ok": True}


@router.post("/cart/checkout")
async def checkout(
    body: CheckoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == current_user.id, Cart.is_active == True)
        .order_by(Cart.created_at.desc())
    )
    # Use the newest active cart and tolerate duplicates: a non-atomic get-or-create
    # in add_to_cart can race two rapid adds into two active carts; scalar_one_or_none
    # would then raise MultipleResultsFound and 500 every checkout for that user.
    cart = result.scalars().first()
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

    subtotal_cents = sum(i.price_cents * i.quantity for i in items)
    item_count = sum(i.quantity for i in items)

    # Reward redemption (PRD-12 / SCRUM-76). A reward only discounts the order if it
    # is the caller's own *issued* reward, not expired, meets the template's minimum,
    # and the atomic issued->redeemed flip wins — so a reward can never be double-spent
    # (mirrors the SCRUM-72 admin-redeem guard).
    discount_cents = 0
    applied_reward = None
    reward_id = body.reward_id if body else None
    if reward_id:
        row = (
            await db.execute(
                select(Reward, RewardTemplate)
                .join(RewardTemplate, Reward.reward_template_id == RewardTemplate.id)
                .where(
                    Reward.id == reward_id,
                    Reward.user_id == current_user.id,
                    Reward.status == "issued",
                )
            )
        ).first()
        if row:
            reward, template = row
            now = datetime.now(timezone.utc)
            not_expired = reward.expires_at is None or reward.expires_at > now
            meets_min = (template.min_order_cents or 0) <= subtotal_cents
            candidate = calculate_discount(
                template.reward_type, template.reward_value, subtotal_cents
            )
            if not_expired and meets_min and candidate > 0:
                redeemed = await db.execute(
                    update(Reward)
                    .where(
                        Reward.id == reward_id,
                        Reward.user_id == current_user.id,
                        Reward.status == "issued",
                    )
                    .values(
                        status="redeemed",
                        redeemed_at=now,
                        redemption_source="checkout",
                    )
                )
                if redeemed.rowcount == 1:
                    discount_cents = candidate
                    applied_reward = reward

    settings = (await db.execute(select(RestaurantSettings))).scalars().first()
    tax_rate = settings.tax_rate if (settings and settings.tax_rate) else 0.0
    currency_symbol = (settings.currency_symbol if settings else None) or "$"

    discounted = subtotal_cents - discount_cents
    # Tax on the post-discount subtotal; round half-up so it matches the SPA's Math.round.
    tax_cents = int(discounted * tax_rate + 0.5) if tax_rate else 0
    total_cents = discounted + tax_cents

    order = OrderModel(
        user_id=current_user.id,
        subtotal_cents=subtotal_cents,
        discount_cents=discount_cents,
        tax_cents=tax_cents,
        total_cents=total_cents,
        reward_id=applied_reward.id if applied_reward else None,
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
        "subtotal_cents": subtotal_cents,
        "discount_cents": discount_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "currency_symbol": currency_symbol,
        "item_count": order.item_count,
        "status": order.status,
        "reward_id": applied_reward.id if applied_reward else None,
        "reward_code": applied_reward.code if applied_reward else None,
    }
