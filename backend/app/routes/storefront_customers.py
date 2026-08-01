"""Front Desk — who is contacting us, and what do we know about them.

The staff tablet's lookup surface. A phone number arrives (typed off a caller
ID, read aloud, or forwarded by an agent) and this returns everything the
restaurant already knows about that person, in one call.

Device-authenticated, not admin-authenticated: staff work the tablet, and every
storefront action is already attributed to a Device. The admin equivalent lives
in ``admin_customers.py`` and is reused by the owner's web view.

A miss is a normal outcome, not an error — most callers early on are strangers.
The response shape is identical either way so the UI has no special case.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_device
from app.models import Device, Order, OrderItem, Reward, User

router = APIRouter(prefix="/api/storefront", tags=["storefront"])

# How many distinct dishes to show as "the usual".
_USUAL_LIMIT = 4
# Orders listed back to staff. Enough to see a pattern, few enough to scan.
_RECENT_ORDER_LIMIT = 5
# Statuses that mean "this is on the pass right now".
_OPEN_ORDER_STATUSES = ("confirmed", "preparing", "ready")


def normalize_phone(raw: str) -> str | None:
    """Digits in, E.164 out. Mirrors schemas.common so lookup matches storage.

    Staff type phone numbers however they are written down — 416-977-3338,
    (416) 977 3338, 4169773338. All of those must find the same customer.
    Returns None when it is not a North American number, so the caller can
    answer "no match" rather than raise.
    """
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return None


@router.get("/customer-lookup")
async def customer_lookup(
    phone: str = Query(..., description="Any format — 4169773338, 416-977-3338, +14169773338"),
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device),
):
    """Everything known about the person on the other end of the line."""
    normalized = normalize_phone(phone)
    if normalized is None:
        return {
            "data": {
                "found": False,
                "phone_input": phone,
                "phone": None,
                "reason": "not_a_north_american_number",
            }
        }

    customer = (
        await db.execute(
            select(User).where(User.phone == normalized, User.role == "customer")
        )
    ).scalar_one_or_none()

    if customer is None:
        # The common case early on. Staff still need the number echoed back
        # cleanly so they can read it aloud to confirm.
        return {"data": {"found": False, "phone_input": phone, "phone": normalized}}

    # --- order history -----------------------------------------------------
    orders = (
        await db.execute(
            select(Order)
            .where(Order.user_id == customer.id)
            .order_by(Order.created_at.desc())
        )
    ).scalars().all()

    open_orders = [o for o in orders if o.status in _OPEN_ORDER_STATUSES]
    recent = orders[:_RECENT_ORDER_LIMIT]

    total_spent_cents = sum(o.total_cents for o in orders)
    first_seen = min((o.created_at for o in orders), default=customer.created_at)

    # --- "the usual" -------------------------------------------------------
    # Ordered by how many they have bought overall, not how recently. Staff
    # recognise a regular by their standing order, not their last one.
    usual_rows = (
        await db.execute(
            select(
                OrderItem.name,
                func.sum(OrderItem.quantity).label("qty"),
                func.count(func.distinct(OrderItem.order_id)).label("times"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.user_id == customer.id)
            .group_by(OrderItem.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(_USUAL_LIMIT)
        )
    ).all()

    # --- rewards -----------------------------------------------------------
    # Only what staff can act on right now. A redeemed reward is history; an
    # unredeemed one is money the customer is about to be reminded of.
    rewards = (
        await db.execute(
            select(Reward)
            .where(Reward.user_id == customer.id)
            .order_by(Reward.issued_at.desc())
        )
    ).scalars().all()

    now = datetime.now(timezone.utc)

    def _is_live(r: Reward) -> bool:
        """Issued, not yet redeemed, not past its expiry."""
        if r.status != "issued":
            return False
        return not (r.expires_at and r.expires_at < now)

    live_rewards = [r for r in rewards if _is_live(r)]

    return {
        "data": {
            "found": True,
            "phone_input": phone,
            "id": customer.id,
            "phone": customer.phone,
            "name": customer.name,
            "email": customer.email,
            "customer_since": (first_seen or customer.created_at).isoformat(),
            "visits": len(orders),
            "total_spent_cents": total_spent_cents,
            "last_order_at": orders[0].created_at.isoformat() if orders else None,
            "usual": [
                {"name": name, "quantity": int(qty), "ordered_in": int(times)}
                for name, qty, times in usual_rows
            ],
            "rewards_live": [
                {
                    "id": r.id,
                    "code": r.code,
                    "issued_at": r.issued_at.isoformat(),
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                }
                for r in live_rewards
            ],
            "rewards_live_count": len(live_rewards),
            "open_orders": [
                {
                    "id": o.id,
                    "status": o.status,
                    "total_cents": o.total_cents,
                    "item_count": o.item_count,
                    "created_at": o.created_at.isoformat(),
                }
                for o in open_orders
            ],
            "recent_orders": [
                {
                    "id": o.id,
                    "status": o.status,
                    "total_cents": o.total_cents,
                    "item_count": o.item_count,
                    "created_at": o.created_at.isoformat(),
                }
                for o in recent
            ],
        }
    }
