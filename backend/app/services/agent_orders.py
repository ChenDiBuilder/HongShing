"""Agent ordering — the service layer behind the restaurant's MCP tools.

A Vela agent (phone or web chat) talks to the restaurant through three verbs:
see the menu, recognise the caller, place the order. Everything here mirrors
the customer checkout money path exactly (subtotal → reward discount → tax on
the discounted amount → total) so an agent-placed order is indistinguishable
from a storefront one on the books.

Design constraints, deliberate:
- Identity before commerce: an order REQUIRES name + phone. That is the
  product thesis — every conversation becomes a customer record.
- Prices come from the menu table, never from the caller.
- Results are structured {"ok": bool, ...} rather than raised errors, so the
  agent can read the reason aloud instead of hearing a stack trace.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.database import AsyncSession
from app.models import (
    Category,
    MenuItem,
    Order,
    OrderItem,
    RestaurantSettings,
    Reward,
    RewardTemplate,
    SignupEvent,
    User,
)
from app.routes.storefront_customers import normalize_phone
from app.services.reward_service import calculate_discount

# One conversation should never turn into a banquet by accident.
MAX_ITEMS_PER_ORDER = 30
MAX_QUANTITY_PER_ITEM = 20


async def menu_snapshot(db: AsyncSession) -> dict:
    """Available menu, grouped by category, prices in cents from the DB."""
    categories = (
        (await db.execute(select(Category).order_by(Category.sort_order, Category.name)))
        .scalars()
        .all()
    )
    items = (
        (
            await db.execute(
                select(MenuItem)
                .where(MenuItem.is_available == True)  # noqa: E712
                .order_by(MenuItem.sort_order, MenuItem.name)
            )
        )
        .scalars()
        .all()
    )
    by_cat: dict[str, list[dict]] = {}
    for m in items:
        by_cat.setdefault(m.category_id, []).append(
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "price_cents": m.price_cents,
                "popular": m.popular,
            }
        )
    return {
        "ok": True,
        "categories": [
            {"name": c.name, "items": by_cat.get(c.id, [])}
            for c in categories
            if by_cat.get(c.id)
        ],
    }


async def customer_context(db: AsyncSession, phone: str) -> dict:
    """What the agent should know about the person it is talking to.

    Compact by design — this lands in a prompt. A stranger is a normal answer.
    """
    normalized = normalize_phone(phone)
    if normalized is None:
        return {"ok": False, "error": "not_a_north_american_number", "phone_input": phone}

    customer = (
        await db.execute(
            select(User).where(User.phone == normalized, User.role == "customer")
        )
    ).scalar_one_or_none()
    if customer is None:
        return {"ok": True, "found": False, "phone": normalized}

    orders = (
        (
            await db.execute(
                select(Order)
                .where(Order.user_id == customer.id, Order.status != "cancelled")
                .order_by(Order.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    usual_rows = (
        await db.execute(
            select(OrderItem.name, func.sum(OrderItem.quantity).label("qty"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.user_id == customer.id, Order.status != "cancelled")
            .group_by(OrderItem.name)
            .order_by(func.sum(OrderItem.quantity).desc(), OrderItem.name.asc())
            .limit(3)
        )
    ).all()

    now = datetime.now(timezone.utc)
    live_rewards = (
        (
            await db.execute(
                select(Reward, RewardTemplate)
                .join(RewardTemplate, RewardTemplate.id == Reward.reward_template_id)
                .where(Reward.user_id == customer.id, Reward.status == "issued")
            )
        )
        .all()
    )
    live = [
        {"code": r.code, "offer": t.name}
        for r, t in live_rewards
        if r.expires_at is None or r.expires_at > now
    ]

    return {
        "ok": True,
        "found": True,
        "phone": normalized,
        "name": customer.name,
        "visits": len(orders),
        "usual": [name for name, _ in usual_rows],
        "live_rewards": live,
        "last_order_at": orders[0].created_at.isoformat() if orders else None,
    }


async def create_agent_order(
    db: AsyncSession,
    phone: str,
    name: str,
    items: list[dict],
    reward_code: str | None = None,
) -> dict:
    """Place an order on behalf of a conversation. Commits on success.

    items: [{"name": "General Tao Chicken", "quantity": 2}, ...] — resolved
    against the live menu by exact (case-insensitive) name.
    """
    normalized = normalize_phone(phone)
    if normalized is None:
        return {"ok": False, "error": "not_a_north_american_number"}
    name = (name or "").strip()
    if not name:
        return {"ok": False, "error": "name_required"}
    if not items:
        return {"ok": False, "error": "no_items"}
    if len(items) > MAX_ITEMS_PER_ORDER:
        return {"ok": False, "error": "too_many_items"}

    # --- resolve items against the menu (prices are ours, not the caller's) --
    resolved: list[tuple[MenuItem, int]] = []
    unknown: list[str] = []
    unavailable: list[str] = []
    for entry in items:
        item_name = str(entry.get("name", "")).strip()
        try:
            quantity = int(entry.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 0
        if not item_name or quantity < 1 or quantity > MAX_QUANTITY_PER_ITEM:
            return {"ok": False, "error": "bad_item_entry", "entry": entry}
        menu_item = (
            await db.execute(
                select(MenuItem).where(func.lower(MenuItem.name) == item_name.lower())
            )
        ).scalars().first()
        if menu_item is None:
            unknown.append(item_name)
        elif not menu_item.is_available:
            unavailable.append(item_name)
        else:
            resolved.append((menu_item, quantity))
    if unknown or unavailable:
        return {
            "ok": False,
            "error": "items_not_on_menu",
            "unknown": unknown,
            "unavailable": unavailable,
        }

    # --- identity: find or create the customer (this IS the capture) ---------
    customer = (
        await db.execute(
            select(User).where(User.phone == normalized, User.role == "customer")
        )
    ).scalar_one_or_none()
    if customer is None:
        customer = User(phone=normalized, name=name, role="customer")
        db.add(customer)
        await db.flush()
        # Attribution: this human was acquired by the agent channel.
        db.add(
            SignupEvent(
                user_id=customer.id,
                phone=normalized,
                source_code="agent",
                signup_method="agent",
            )
        )
    elif not customer.name:
        customer.name = name

    # --- money path: mirrors /cart/checkout exactly --------------------------
    subtotal_cents = sum(m.price_cents * q for m, q in resolved)
    item_count = sum(q for _, q in resolved)

    discount_cents = 0
    applied_reward = None
    if reward_code:
        row = (
            await db.execute(
                select(Reward, RewardTemplate)
                .join(RewardTemplate, Reward.reward_template_id == RewardTemplate.id)
                .where(
                    Reward.code == reward_code.strip().upper(),
                    Reward.user_id == customer.id,
                    Reward.status == "issued",
                )
            )
        ).first()
        if row is None:
            return {"ok": False, "error": "reward_not_usable", "reward_code": reward_code}
        reward, template = row
        now = datetime.now(timezone.utc)
        if reward.expires_at is not None and reward.expires_at <= now:
            return {"ok": False, "error": "reward_expired", "reward_code": reward.code}
        if (template.min_order_cents or 0) > subtotal_cents:
            return {
                "ok": False,
                "error": "reward_minimum_not_met",
                "min_order_cents": template.min_order_cents,
            }
        candidate = calculate_discount(
            template.reward_type, template.reward_value, subtotal_cents
        )
        if candidate > 0:
            redeemed = await db.execute(
                update(Reward)
                .where(
                    Reward.id == reward.id,
                    Reward.user_id == customer.id,
                    Reward.status == "issued",
                )
                .values(
                    status="redeemed",
                    redeemed_at=now,
                    redemption_source="agent",
                )
            )
            if redeemed.rowcount == 1:
                discount_cents = candidate
                applied_reward = reward

    settings = (await db.execute(select(RestaurantSettings))).scalars().first()
    tax_rate = settings.tax_rate if (settings and settings.tax_rate) else 0.0
    discounted = subtotal_cents - discount_cents
    # Tax on the post-discount subtotal; round half-up, matching the SPA.
    tax_cents = int(discounted * tax_rate + 0.5) if tax_rate else 0
    total_cents = discounted + tax_cents

    order = Order(
        user_id=customer.id,
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
    for menu_item, quantity in resolved:
        db.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                name=menu_item.name,
                price_cents=menu_item.price_cents,
                quantity=quantity,
            )
        )
    await db.commit()

    return {
        "ok": True,
        "order_id": order.id,
        "status": order.status,
        "items": [
            {"name": m.name, "quantity": q, "price_cents": m.price_cents}
            for m, q in resolved
        ],
        "subtotal_cents": subtotal_cents,
        "discount_cents": discount_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "reward_applied": applied_reward.code if applied_reward else None,
        "customer": {"phone": normalized, "name": customer.name},
    }


async def order_status(db: AsyncSession, order_id: str) -> dict:
    order = (
        await db.execute(select(Order).where(Order.id == order_id))
    ).scalar_one_or_none()
    if order is None:
        return {"ok": False, "error": "order_not_found"}
    return {
        "ok": True,
        "order_id": order.id,
        "status": order.status,
        "total_cents": order.total_cents,
        "item_count": order.item_count,
        "created_at": order.created_at.isoformat(),
    }
