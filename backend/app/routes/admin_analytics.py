from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text, union_all, literal_column, literal

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import (
    Order,
    OrderItem,
    User,
    QRScanEvent,
    SignupEvent,
    Reward,
    ExternalOrderRedirect,
    UserNotificationPreference,
    QRCampaign,
)

router = APIRouter()


async def _count_scans(db: AsyncSession, since: datetime) -> int:
    c = await db.scalar(
        select(func.count(QRScanEvent.id)).where(
            QRScanEvent.event_type == "scan_confirmed",
            QRScanEvent.is_likely_bot == False,  # noqa: E712
            QRScanEvent.created_at >= since,
        )
    )
    return c or 0


async def _count_signups(db: AsyncSession, since: datetime) -> int:
    c = await db.scalar(
        select(func.count(SignupEvent.id)).where(SignupEvent.created_at >= since)
    )
    return c or 0


async def _count_rewards_issued(db: AsyncSession, since: datetime) -> int:
    c = await db.scalar(
        select(func.count(Reward.id)).where(
            Reward.status == "issued", Reward.issued_at >= since
        )
    )
    return c or 0


async def _count_rewards_redeemed(db: AsyncSession, since: datetime) -> int:
    c = await db.scalar(
        select(func.count(Reward.id)).where(
            Reward.status == "redeemed", Reward.redeemed_at >= since
        )
    )
    return c or 0


async def _count_redirects(db: AsyncSession, since: datetime) -> int:
    c = await db.scalar(
        select(func.count(ExternalOrderRedirect.id)).where(
            ExternalOrderRedirect.created_at >= since
        )
    )
    return c or 0


async def _count_orders(db: AsyncSession, since: datetime) -> int:
    c = await db.scalar(
        select(func.count(Order.id)).where(Order.created_at >= since)
    )
    return c or 0


async def _order_revenue(db: AsyncSession, since: datetime) -> int:
    c = await db.scalar(
        select(func.coalesce(func.sum(Order.total_cents), 0)).where(
            Order.created_at >= since
        )
    )
    return c or 0


async def _source_breakdown(db: AsyncSession, since: datetime) -> list[dict]:
    sources = {}

    scan_rows = await db.execute(
        select(
            QRScanEvent.source_code,
            func.count(QRScanEvent.id).label("cnt"),
        )
        .where(
            QRScanEvent.event_type == "scan_confirmed",
            QRScanEvent.is_likely_bot == False,  # noqa: E712
            QRScanEvent.created_at >= since,
        )
        .group_by(QRScanEvent.source_code)
    )
    for row in scan_rows.all():
        sc = row.source_code or "unknown"
        sources.setdefault(sc, {})["scans"] = row.cnt

    signup_rows = await db.execute(
        select(
            SignupEvent.source_code,
            func.count(SignupEvent.id).label("cnt"),
        )
        .where(SignupEvent.created_at >= since)
        .group_by(SignupEvent.source_code)
    )
    for row in signup_rows.all():
        sc = row.source_code or "unknown"
        sources.setdefault(sc, {})["signups"] = row.cnt

    reward_rows = await db.execute(
        select(
            Reward.source_code,
            func.count(Reward.id).label("cnt"),
        )
        .where(Reward.issued_at >= since)
        .group_by(Reward.source_code)
    )
    for row in reward_rows.all():
        sc = row.source_code or "unknown"
        sources.setdefault(sc, {})["rewards_issued"] = row.cnt

    redirect_rows = await db.execute(
        select(
            ExternalOrderRedirect.source_code,
            func.count(ExternalOrderRedirect.id).label("cnt"),
        )
        .where(ExternalOrderRedirect.created_at >= since)
        .group_by(ExternalOrderRedirect.source_code)
    )
    for row in redirect_rows.all():
        sc = row.source_code or "unknown"
        sources.setdefault(sc, {})["redirects"] = row.cnt

    result = []
    for sc, counts in sources.items():
        campaign_name = None
        if sc != "unknown":
            name = await db.scalar(
                select(QRCampaign.name).where(QRCampaign.source_code == sc)
            )
            campaign_name = name
        result.append(
            {
                "source_code": sc,
                "campaign_name": campaign_name,
                "scans": counts.get("scans", 0),
                "signups": counts.get("signups", 0),
                "rewards_issued": counts.get("rewards_issued", 0),
                "redirects": counts.get("redirects", 0),
            }
        )

    result.sort(key=lambda x: x["scans"], reverse=True)
    return result


async def _recent_activity(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Fetch recent events from scans, signups, rewards, redirects, orders."""
    items = []

    scans = await db.execute(
        select(QRScanEvent)
        .where(
            QRScanEvent.event_type == "scan_confirmed",
            QRScanEvent.is_likely_bot == False,  # noqa: E712
        )
        .order_by(QRScanEvent.created_at.desc())
        .limit(limit)
    )
    for s in scans.scalars().all():
        items.append(
            {
                "type": "scan",
                "source_code": s.source_code,
                "created_at": s.created_at.isoformat(),
                "detail": None,
            }
        )

    signups = await db.execute(
        select(SignupEvent, User)
        .join(User, SignupEvent.user_id == User.id, isouter=True)
        .order_by(SignupEvent.created_at.desc())
        .limit(limit)
    )
    for s, u in signups.all():
        items.append(
            {
                "type": "signup",
                "source_code": s.source_code,
                "created_at": s.created_at.isoformat(),
                "detail": u.phone[-4:] if u and u.phone else None,
            }
        )

    rewards = await db.execute(
        select(Reward)
        .order_by(Reward.issued_at.desc())
        .limit(limit)
    )
    for r in rewards.scalars().all():
        items.append(
            {
                "type": "reward_issued",
                "source_code": r.source_code,
                "created_at": r.issued_at.isoformat(),
                "detail": r.code,
            }
        )

    redeemed = await db.execute(
        select(Reward)
        .where(Reward.status == "redeemed")
        .order_by(Reward.redeemed_at.desc())
        .limit(limit)
    )
    for r in redeemed.scalars().all():
        ts = r.redeemed_at.isoformat() if r.redeemed_at else r.issued_at.isoformat()
        items.append(
            {
                "type": "reward_redeemed",
                "source_code": r.source_code,
                "created_at": ts,
                "detail": r.code,
            }
        )

    redirects = await db.execute(
        select(ExternalOrderRedirect)
        .order_by(ExternalOrderRedirect.created_at.desc())
        .limit(limit)
    )
    for r in redirects.scalars().all():
        items.append(
            {
                "type": "redirect",
                "source_code": r.source_code,
                "created_at": r.created_at.isoformat(),
                "detail": r.provider,
            }
        )

    orders = await db.execute(
        select(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    for o in orders.scalars().all():
        items.append(
            {
                "type": "order",
                "source_code": None,
                "created_at": o.created_at.isoformat(),
                "detail": f"${o.total_cents / 100:.2f}",
            }
        )

    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items[:limit]


@router.get("/analytics")
async def analytics(
    days: int = Query(14, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    scans_today = await _count_scans(db, today_start)
    scans_period = await _count_scans(db, since)
    signups_today = await _count_signups(db, today_start)
    signups_period = await _count_signups(db, since)
    rewards_issued_today = await _count_rewards_issued(db, today_start)
    rewards_issued_period = await _count_rewards_issued(db, since)
    rewards_redeemed_today = await _count_rewards_redeemed(db, today_start)
    rewards_redeemed_period = await _count_rewards_redeemed(db, since)
    redirects_today = await _count_redirects(db, today_start)
    redirects_period = await _count_redirects(db, since)
    orders_today = await _count_orders(db, today_start)
    orders_period = await _count_orders(db, since)
    revenue_today = await _order_revenue(db, today_start)
    revenue_period = await _order_revenue(db, since)

    sent_opt_in = await db.scalar(
        select(func.count(UserNotificationPreference.user_id)).where(
            UserNotificationPreference.sms_marketing_opt_in == True,  # noqa: E712
        )
    )
    total_prefs = await db.scalar(
        select(func.count(UserNotificationPreference.user_id))
    )
    sms_opt_in_rate = (
        round(sent_opt_in / total_prefs * 100, 1) if total_prefs else 0.0
    )

    daily_volume_rows = await db.execute(
        select(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(Order.total_cents), 0).label("revenue"),
        )
        .where(Order.created_at >= since)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at).asc())
    )
    volume_data = [
        {"day": str(row.day), "orders": row.count, "revenue_cents": row.revenue}
        for row in daily_volume_rows.all()
    ]

    top_dishes_rows = await db.execute(
        select(
            OrderItem.name,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.count(func.distinct(OrderItem.order_id)).label("order_count"),
        )
        .where(OrderItem.created_at >= since)
        .group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
    )
    dishes_data = [
        {
            "name": row.name,
            "total_quantity": row.total_qty,
            "order_count": row.order_count,
        }
        for row in top_dishes_rows.all()
    ]

    status_rows = await db.execute(
        select(Order.status, func.count(Order.id).label("count"))
        .where(Order.created_at >= since)
        .group_by(Order.status)
    )
    status_data = {row.status: row.count for row in status_rows.all()}

    sources = await _source_breakdown(db, since)
    recent = await _recent_activity(db, limit=20)

    return {
        "data": {
            "summary": {
                "today": {
                    "scans": scans_today,
                    "signups": signups_today,
                    "rewards_issued": rewards_issued_today,
                    "rewards_redeemed": rewards_redeemed_today,
                    "redirects": redirects_today,
                    "orders": orders_today,
                    "revenue_cents": revenue_today,
                },
                "period": {
                    "scans": scans_period,
                    "signups": signups_period,
                    "rewards_issued": rewards_issued_period,
                    "rewards_redeemed": rewards_redeemed_period,
                    "redirects": redirects_period,
                    "orders": orders_period,
                    "revenue_cents": revenue_period,
                },
            },
            "funnel": {
                "qr_scans": scans_period,
                "signups": signups_period,
                "rewards_issued": rewards_issued_period,
                "redirects": redirects_period,
                "orders": orders_period,
            },
            "sources": sources,
            "sms_opt_in_rate": sms_opt_in_rate,
            "daily_volume": volume_data,
            "top_dishes": dishes_data,
            "status_breakdown": status_data,
            "recent_activity": recent,
            "days": days,
        }
    }
