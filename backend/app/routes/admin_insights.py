"""This Week — the owner's decision surface.

GET /api/admin/insights returns ranked, plain-language recommendation cards,
each carrying the evidence behind it and (where one exists) a concrete action.
POST /api/admin/insights/act executes that action — issuing rewards and/or
sending CASL-gated texts — and logs it as an InsightAction whose outcomes
(redemptions, return revenue) are computed live on every subsequent GET.

Decide → act → measure, all on one screen. The segment math lives in
app/services/decisioning.py; this module only assembles rows and executes.
"""
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import (
    InsightAction,
    Notification,
    Order,
    OrderItem,
    QRScanEvent,
    RestaurantSettings,
    Reward,
    RewardTemplate,
    SignupEvent,
    User,
    UserNotificationPreference,
)
from app.services import decisioning as dec
from app.services.reward_service import (
    DEFAULT_REWARD_SMS_TEMPLATE,
    generate_reward_code,
    render_reward_sms,
    should_send_reward_sms,
)
# Module (not symbol) import so the tests' autouse SNS stub — which patches the
# attribute on sms_service — also intercepts sends from this route.
from app.services import sms_service

router = APIRouter()

# Orders in any of these states never count as a visit.
_EXCLUDED_ORDER_STATUSES = ("cancelled",)

# One action may target at most this many people/rewards.
_ACT_MAX_TARGETS = 200
# Evidence rows ARE the actionable list — the UI builds its targets from them —
# so the caps must match or holders past the evidence cap would silently never
# be reachable. The headline count is always the true total and the card says
# when it is showing a subset.
_EVIDENCE_CAP = _ACT_MAX_TARGETS

# Reminder body for rewards about to expire. Rendered through render_reward_sms,
# which appends the CASL footer (mailing address + STOP).
REMINDER_SMS_TEMPLATE = (
    "{restaurant}: your reward {reward_code} expires soon — "
    "use it on your next order: {ordering_url}"
)

_ACTIONABLE_INSIGHTS = {
    "lapsed_regulars": "send_offer",
    "one_and_done": "send_offer",
    "expiring_rewards": "send_reminder",
}


# --------------------------------------------------------------------------
# Assembly helpers — rows out of the DB, shaped for the pure layer.
# --------------------------------------------------------------------------

async def _customer_histories(db: AsyncSession) -> list[dec.CustomerHistory]:
    rows = (
        await db.execute(
            select(
                Order.user_id,
                Order.created_at,
                Order.total_cents,
                User.name,
                User.phone,
            )
            .join(User, User.id == Order.user_id)
            .where(
                User.role == "customer",
                Order.status.notin_(_EXCLUDED_ORDER_STATUSES),
            )
            .order_by(Order.created_at.asc())
        )
    ).all()

    by_user: dict[str, dec.CustomerHistory] = {}
    for user_id, created_at, total_cents, name, phone in rows:
        h = by_user.get(user_id)
        if h is None:
            h = dec.CustomerHistory(user_id=user_id, name=name, phone=phone)
            by_user[user_id] = h
        h.order_times.append(created_at)
        h.total_spent_cents += total_cents
    return list(by_user.values())


async def _usual_items(db: AsyncSession, user_ids: list[str]) -> dict[str, str]:
    """Each surfaced customer's most-bought dish, for the evidence rows."""
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(
                Order.user_id,
                OrderItem.name,
                func.sum(OrderItem.quantity).label("qty"),
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.user_id.in_(user_ids),
                Order.status.notin_(_EXCLUDED_ORDER_STATUSES),
            )
            .group_by(Order.user_id, OrderItem.name)
            .order_by(func.sum(OrderItem.quantity).desc(), OrderItem.name.asc())
        )
    ).all()
    usual: dict[str, str] = {}
    for user_id, name, _qty in rows:
        usual.setdefault(user_id, name)
    return usual


async def _expiring_rewards(db: AsyncSession, now: datetime) -> list[dict]:
    horizon = now + timedelta(days=dec.EXPIRING_WINDOW_DAYS)
    rows = (
        await db.execute(
            select(Reward, User.name, User.phone, RewardTemplate.name)
            .join(User, User.id == Reward.user_id)
            .join(RewardTemplate, RewardTemplate.id == Reward.reward_template_id)
            .where(
                Reward.status == "issued",
                Reward.expires_at.isnot(None),
                Reward.expires_at > now,
                Reward.expires_at <= horizon,
            )
            .order_by(Reward.expires_at.asc())
        )
    ).all()
    return [
        {
            "reward_id": r.id,
            "code": r.code,
            "expires_at": r.expires_at.isoformat(),
            "days_left": max(0, round((r.expires_at - now).total_seconds() / 86400, 1)),
            "user_id": r.user_id,
            "name": user_name,
            "phone": phone,
            "template_name": template_name,
        }
        for r, user_name, phone, template_name in rows
    ]


async def _slow_day(
    db: AsyncSession, settings_row: RestaurantSettings | None, now: datetime
) -> dict:
    since = now - timedelta(days=dec.SLOW_DAY_WINDOW_DAYS)
    rows = (
        await db.execute(
            select(Order.created_at, Order.total_cents).where(
                Order.created_at >= since,
                Order.status.notin_(_EXCLUDED_ORDER_STATUSES),
            )
        )
    ).all()
    tz_name = (settings_row.timezone if settings_row else None) or "America/Toronto"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/Toronto")

    daily: dict = {}
    for created_at, total_cents in rows:
        local_date = created_at.astimezone(tz).date()
        daily[local_date] = daily.get(local_date, 0) + total_cents
    # Only complete local days may enter a weekday's average: today is still in
    # progress and the window's first day is truncated by the cutoff — and with
    # a 56-day window both land on the SAME weekday, depressing it twice.
    daily.pop(now.astimezone(tz).date(), None)
    daily.pop(since.astimezone(tz).date(), None)
    return dec.slow_day_assessment(sorted(daily.items()))


async def _template_performance(db: AsyncSession, now: datetime) -> list[dict]:
    """Cohort = rewards ISSUED in the window; rate = share of it now redeemed;
    revenue = orders that consumed those rewards."""
    since = now - timedelta(days=dec.TEMPLATE_WINDOW_DAYS)
    rows = (
        await db.execute(
            select(
                RewardTemplate.id,
                RewardTemplate.name,
                RewardTemplate.reward_type,
                RewardTemplate.reward_value,
                func.count(Reward.id).label("issued"),
                func.count(Reward.id).filter(Reward.status == "redeemed").label("redeemed"),
            )
            .join(Reward, Reward.reward_template_id == RewardTemplate.id)
            .where(Reward.issued_at >= since)
            .group_by(
                RewardTemplate.id,
                RewardTemplate.name,
                RewardTemplate.reward_type,
                RewardTemplate.reward_value,
            )
        )
    ).all()
    out = []
    for tid, name, rtype, rvalue, issued, redeemed in rows:
        revenue = await db.scalar(
            select(func.coalesce(func.sum(Order.total_cents), 0))
            .join(Reward, Reward.id == Order.reward_id)
            .where(
                Reward.reward_template_id == tid,
                Reward.issued_at >= since,
                Order.status.notin_(_EXCLUDED_ORDER_STATUSES),
            )
        )
        out.append(
            {
                "template_id": tid,
                "name": name,
                "reward_type": rtype,
                "reward_value": rvalue,
                "issued": issued,
                "redeemed": redeemed,
                "revenue_cents": revenue or 0,
            }
        )
    return out


async def _campaign_rows(db: AsyncSession, now: datetime) -> list[dict]:
    since = now - timedelta(days=dec.CAMPAIGN_WINDOW_DAYS)
    scan_rows = (
        await db.execute(
            select(QRScanEvent.source_code, func.count(QRScanEvent.id))
            .where(
                QRScanEvent.event_type == "scan_confirmed",
                QRScanEvent.is_likely_bot == False,  # noqa: E712
                QRScanEvent.created_at >= since,
                QRScanEvent.source_code.isnot(None),
            )
            .group_by(QRScanEvent.source_code)
        )
    ).all()
    signup_rows = (
        await db.execute(
            select(SignupEvent.source_code, func.count(SignupEvent.id))
            .where(SignupEvent.created_at >= since, SignupEvent.source_code.isnot(None))
            .group_by(SignupEvent.source_code)
        )
    ).all()
    signups = {sc: n for sc, n in signup_rows}

    from app.models import QRCampaign

    out = []
    for sc, scans in scan_rows:
        name = await db.scalar(select(QRCampaign.name).where(QRCampaign.source_code == sc))
        out.append(
            {
                "source_code": sc,
                "campaign_name": name,
                "scans": scans,
                "signups": signups.get(sc, 0),
            }
        )
    return out


async def _actions_with_outcomes(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Past decisions with live results. Only post-action redemptions count."""
    actions = (
        (
            await db.execute(
                select(InsightAction)
                .order_by(InsightAction.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    out = []
    for a in actions:
        if a.action_type == "send_offer":
            reward_filter = Reward.source_code == a.source_code
        else:
            reward_ids = (a.params or {}).get("reward_ids", [])
            if not reward_ids:
                reward_filter = Reward.id.is_(None)  # matches nothing
            else:
                # A reminder may target rewards an earlier offer action minted
                # (they expire too). Their redemptions credit the offer that
                # created them — counting both would double the revenue.
                # source_code is nullable: NULL NOT LIKE ... is NULL, which
                # would silently drop organically-claimed rewards, so the null
                # case must be admitted explicitly.
                reward_filter = Reward.id.in_(reward_ids) & (
                    Reward.source_code.is_(None) | Reward.source_code.notlike("dec-%")
                )

        redeemed = await db.scalar(
            select(func.count(Reward.id)).where(
                reward_filter,
                Reward.status == "redeemed",
                Reward.redeemed_at > a.created_at,
            )
        )
        revenue = await db.scalar(
            select(func.coalesce(func.sum(Order.total_cents), 0))
            .join(Reward, Reward.id == Order.reward_id)
            .where(
                reward_filter,
                Order.created_at > a.created_at,
                Order.status.notin_(_EXCLUDED_ORDER_STATUSES),
            )
        )
        template_name = None
        if a.reward_template_id:
            template_name = await db.scalar(
                select(RewardTemplate.name).where(RewardTemplate.id == a.reward_template_id)
            )
        out.append(
            {
                "id": a.id,
                "insight_key": a.insight_key,
                "action_type": a.action_type,
                "template_name": template_name,
                "created_at": a.created_at.isoformat(),
                "targeted_count": a.targeted_count,
                "rewards_issued": a.rewards_issued,
                "already_had": a.already_had,
                "sms_sent": a.sms_sent,
                "sms_skipped": a.sms_skipped,
                "outcome": {
                    "redeemed": redeemed or 0,
                    "revenue_cents": revenue or 0,
                },
            }
        )
    return out


# --------------------------------------------------------------------------
# Card copy — plain words an owner can check on a napkin.
# --------------------------------------------------------------------------

def _build_cards(
    segments: dict,
    expiring: list[dict],
    slow: dict,
    verdicts: dict,
    leak: dict | None,
    usual: dict[str, str],
) -> list[dict]:
    cards: list[dict] = []

    def with_usual(people: list[dict]) -> list[dict]:
        return [
            {**p, "usual": usual.get(p["user_id"])} for p in people[:_EVIDENCE_CAP]
        ]

    if expiring:
        cards.append(
            {
                "key": "expiring_rewards",
                "priority": "act_now",
                "headline": f"{len(expiring)} reward{'s' if len(expiring) != 1 else ''} die within a week",
                "why": (
                    "These were already promised. If they expire unseen, the promise "
                    "cost goodwill and brought nobody back. A nudge costs one text."
                ),
                "impact_cents": None,
                "evidence": {"rewards": expiring[:_EVIDENCE_CAP], "total": len(expiring)},
                "action": {"type": "send_reminder"},
            }
        )

    lapsed = segments["lapsed"]
    if lapsed:
        impact = dec.estimated_return_cents(lapsed)
        cards.append(
            {
                "key": "lapsed_regulars",
                "priority": "act_now" if len(lapsed) >= 3 else "worth_doing",
                "headline": f"{len(lapsed)} regular{'s have' if len(lapsed) != 1 else ' has'} gone quiet",
                "why": (
                    "Each of these people had a rhythm — every week or two, same "
                    "dishes — and it stopped. Winning back someone who already loved "
                    "you is far cheaper than finding a stranger."
                ),
                "impact_cents": impact,
                "impact_label": "if a third come back once, at their usual ticket",
                "evidence": {"people": with_usual(lapsed), "total": len(lapsed)},
                "action": {"type": "send_offer"},
            }
        )

    ones = segments["one_and_done"]
    if ones:
        impact = dec.estimated_return_cents(ones)
        cards.append(
            {
                "key": "one_and_done",
                "priority": "worth_doing",
                "headline": f"{len(ones)} first-timer{'s' if len(ones) != 1 else ''} never came back",
                "why": (
                    "They tried you once, two weeks to two months ago, and went "
                    "quiet. The second visit is the hardest one — make it feel like "
                    "an invitation, not an ad."
                ),
                "impact_cents": impact,
                "impact_label": "if a third return once",
                "evidence": {"people": with_usual(ones), "total": len(ones)},
                "action": {"type": "send_offer"},
            }
        )

    if slow.get("status") == "ok" and slow.get("fires"):
        s = slow["slowest"]
        cards.append(
            {
                "key": "slow_day",
                "priority": "worth_doing",
                "headline": f"{s['weekday']}s are your quietest day",
                "why": (
                    f"A typical {s['weekday']} brings in about "
                    f"${s['avg_revenue_cents'] / 100:,.0f} — "
                    f"{s['pct_of_median']}% of a normal day. An offer that fills a "
                    "slow room beats one discounting a busy one: point your next "
                    f"promotion at {s['weekday']}s."
                ),
                "impact_cents": None,
                "evidence": {"weekdays": slow["weekdays"], "median_avg_cents": slow["median_avg_cents"]},
                "action": None,
            }
        )

    dud = verdicts.get("dud")
    if dud:
        cards.append(
            {
                "key": "reward_dud",
                "priority": "worth_doing",
                "headline": f'"{dud["name"]}" isn\'t landing',
                "why": (
                    f"Issued {dud['issued']} times in 90 days, used "
                    f"{dud['redeemed']} time{'s' if dud['redeemed'] != 1 else ''} "
                    f"({round(dud['redemption_rate'] * 100)}%). People take it and "
                    "forget it — the offer, the wording, or the window is wrong. "
                    "Change one of the three."
                ),
                "impact_cents": None,
                "evidence": {"template": dud},
                "action": None,
            }
        )

    if leak:
        best, worst = leak["best"], leak["leak"]
        cards.append(
            {
                "key": "campaign_leak",
                "priority": "watch",
                "headline": f"The {worst['campaign_name'] or worst['source_code']} placement isn't converting",
                "why": (
                    f"{worst['scans']} scans became {worst['signups']} signups "
                    f"({round(worst['rate'] * 100)}%), while "
                    f"{best['campaign_name'] or best['source_code']} converts at "
                    f"{round(best['rate'] * 100)}%. Same offer, different spot — "
                    "move the card or change what it says."
                ),
                "impact_cents": None,
                "evidence": {"best": best, "leak": worst},
                "action": None,
            }
        )

    winner = verdicts.get("winner")
    if winner:
        cards.append(
            {
                "key": "reward_winner",
                "priority": "watch",
                "headline": f'"{winner["name"]}" is doing the work',
                "why": (
                    f"{round(winner['redemption_rate'] * 100)}% of the "
                    f"{winner['issued']} issued in 90 days came back and were used, "
                    f"bringing ${winner['revenue_cents'] / 100:,.0f} through the "
                    "door. When in doubt, this is the offer to lead with."
                ),
                "impact_cents": None,
                "evidence": {"template": winner},
                "action": None,
            }
        )

    vips = segments["vips"]
    if vips:
        cards.append(
            {
                "key": "vips",
                "priority": "watch",
                "headline": f"{len(vips)} names worth knowing",
                "why": (
                    "Your biggest spenders who still come regularly. Don't discount "
                    "them — they already come; a reward here is margin given away. "
                    "Greet them by name: they appear on the Front Desk screen "
                    "whenever they call."
                ),
                "impact_cents": None,
                "evidence": {"people": with_usual(vips), "total": len(vips)},
                "action": None,
            }
        )

    if slow.get("status") == "insufficient":
        cards.append(
            {
                "key": "slow_day_locked",
                "priority": "locked",
                "headline": "Quiet-day analysis needs more history",
                "why": (
                    f"Weekday patterns need about {slow['need_days']} days of orders "
                    f"to mean anything; there are {slow['have_days']} so far. This "
                    "unlocks by itself."
                ),
                "impact_cents": None,
                "evidence": None,
                "action": None,
            }
        )

    return cards


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@router.get("/insights")
async def get_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    now = datetime.now(timezone.utc)
    settings_row = (await db.execute(select(RestaurantSettings))).scalars().first()

    histories = await _customer_histories(db)
    segments = dec.classify_customers(histories, now)

    surfaced_ids = [
        p["user_id"]
        for seg in ("lapsed", "one_and_done", "vips")
        for p in segments[seg]
    ]
    usual = await _usual_items(db, surfaced_ids)

    expiring = await _expiring_rewards(db, now)
    slow = await _slow_day(db, settings_row, now)
    verdicts = dec.template_verdicts(await _template_performance(db, now))
    leak = dec.campaign_leaks(await _campaign_rows(db, now))

    cards = _build_cards(segments, expiring, slow, verdicts, leak, usual)

    templates = (
        (
            await db.execute(
                select(RewardTemplate)
                .where(RewardTemplate.active == True)  # noqa: E712
                .order_by(RewardTemplate.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    order_times = [t for h in histories for t in h.order_times]
    coverage = {
        "orders": len(order_times),
        "customers": len(histories),
        "first_order_at": min(order_times).isoformat() if order_times else None,
        "last_order_at": max(order_times).isoformat() if order_times else None,
    }

    return {
        "data": {
            "coverage": coverage,
            "cards": cards,
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "reward_type": t.reward_type,
                    "reward_value": t.reward_value,
                    "valid_days": t.valid_days,
                }
                for t in templates
            ],
            "default_template_id": settings_row.default_reward_template_id
            if settings_row
            else None,
            # Whether marketing texts can go out at all. The mailing address is
            # the one hard requirement (CASL footer); both send paths fall back
            # to a default body when no template is configured, so the flag and
            # the actual gate can't disagree. The UI explains skips honestly
            # instead of failing silently.
            "sms_configured": bool(settings_row and settings_row.business_mailing_address),
            "actions": await _actions_with_outcomes(db),
        }
    }


class ActRequest(BaseModel):
    insight_key: str
    action_type: str
    template_id: str | None = None
    user_ids: list[str] = Field(default_factory=list)
    reward_ids: list[str] = Field(default_factory=list)


@router.post("/insights/act")
async def act_on_insight(
    body: ActRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    expected = _ACTIONABLE_INSIGHTS.get(body.insight_key)
    if expected is None or body.action_type != expected:
        raise HTTPException(status_code=400, detail="Unknown insight or action")

    now = datetime.now(timezone.utc)
    settings_row = (await db.execute(select(RestaurantSettings))).scalars().first()
    mailing = settings_row.business_mailing_address if settings_row else None
    restaurant_name = settings_row.restaurant_name if settings_row else "Restaurant"
    ordering_url = (
        (settings_row.external_ordering_url or settings_row.public_domain or "")
        if settings_row
        else ""
    )

    source_code = f"dec-{secrets.token_hex(4)}"
    queued_sms: list[tuple[str, str]] = []  # (phone, body) — sent only after commit

    if body.action_type == "send_offer":
        if not body.template_id or not body.user_ids:
            raise HTTPException(status_code=400, detail="template_id and user_ids required")
        if len(body.user_ids) > _ACT_MAX_TARGETS:
            raise HTTPException(status_code=400, detail=f"At most {_ACT_MAX_TARGETS} people per action")

        template = (
            await db.execute(
                select(RewardTemplate).where(
                    RewardTemplate.id == body.template_id,
                    RewardTemplate.active == True,  # noqa: E712
                )
            )
        ).scalar_one_or_none()
        if template is None:
            raise HTTPException(status_code=404, detail="Reward template not found")

        users = (
            (
                await db.execute(
                    select(User).where(
                        User.id.in_(body.user_ids), User.role == "customer"
                    )
                )
            )
            .scalars()
            .all()
        )
        if not users:
            raise HTTPException(status_code=400, detail="No matching customers")

        prefs_rows = (
            await db.execute(
                select(UserNotificationPreference).where(
                    UserNotificationPreference.user_id.in_([u.id for u in users])
                )
            )
        ).scalars().all()
        prefs = {p.user_id: p for p in prefs_rows}

        # Nothing else in the system ever flips a reward past its expiry off
        # status='issued', and the one-issued-per-(user, template) partial index
        # matches on status alone — so a long-dead reward would block the new
        # offer and get miscounted as "already has one". The people this feature
        # targets (gone 2 weeks to 4 months) are exactly the people holding
        # expired rewards. Retire those first; only genuinely LIVE rewards count
        # as already-had.
        await db.execute(
            update(Reward)
            .where(
                Reward.user_id.in_([u.id for u in users]),
                Reward.reward_template_id == template.id,
                Reward.status == "issued",
                Reward.expires_at.isnot(None),
                Reward.expires_at < now,
            )
            .values(status="expired")
        )

        expires_at = now + timedelta(days=template.valid_days)
        issued = already_had = sms_sent = sms_skipped = 0

        for user in users:
            code = generate_reward_code(template.code_prefix)
            for _ in range(5):
                exists = await db.scalar(select(Reward.id).where(Reward.code == code))
                if not exists:
                    break
                code = generate_reward_code(template.code_prefix)

            # Same race-safe pattern as the customer claim flow: the partial
            # unique index allows one ISSUED reward per (user, template).
            new_id = (
                await db.execute(
                    pg_insert(Reward)
                    .values(
                        user_id=user.id,
                        reward_template_id=template.id,
                        code=code,
                        source_code=source_code,
                        status="issued",
                        expires_at=expires_at,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["user_id", "reward_template_id"],
                        index_where=text("status = 'issued'"),
                    )
                    .returning(Reward.id)
                )
            ).scalar()

            if new_id is None:
                already_had += 1
                continue
            issued += 1

            p = prefs.get(user.id)
            consent = bool(p and p.sms_marketing_opt_in)
            # Fall back to the stock body so a missing template config can't
            # silently disable texting that sms_configured said was on.
            sms_template = (
                settings_row.reward_sms_template if settings_row else None
            ) or DEFAULT_REWARD_SMS_TEMPLATE
            if should_send_reward_sms(consent, mailing, sms_template, user.phone):
                sms_body = render_reward_sms(
                    sms_template, restaurant_name, code, ordering_url, mailing
                )
                queued_sms.append((user.phone, sms_body))
                db.add(
                    Notification(
                        sender_id=current_user.id,
                        recipient_id=user.id,
                        title="Offer from This Week",
                        body=sms_body,
                        channel="sms",
                        message_type="marketing",
                        status="sent",
                    )
                )
                sms_sent += 1
            else:
                sms_skipped += 1

        action = InsightAction(
            insight_key=body.insight_key,
            action_type=body.action_type,
            source_code=source_code,
            reward_template_id=template.id,
            acted_by=current_user.id,
            targeted_count=len(users),
            rewards_issued=issued,
            already_had=already_had,
            sms_sent=sms_sent,
            sms_skipped=sms_skipped,
            params={"user_ids": [u.id for u in users]},
        )

    else:  # send_reminder
        if not body.reward_ids:
            raise HTTPException(status_code=400, detail="reward_ids required")
        if len(body.reward_ids) > _ACT_MAX_TARGETS:
            raise HTTPException(status_code=400, detail=f"At most {_ACT_MAX_TARGETS} rewards per action")

        # Re-validate server-side exactly what the GET card promised: live
        # rewards, held by customers, genuinely inside the expiry window. A
        # stale page (or a hand-crafted request) must not text "expires soon"
        # about a reward that already died or has weeks left.
        horizon = now + timedelta(days=dec.EXPIRING_WINDOW_DAYS)
        rows = (
            await db.execute(
                select(Reward, User)
                .join(User, User.id == Reward.user_id)
                .where(
                    Reward.id.in_(body.reward_ids),
                    Reward.status == "issued",
                    User.role == "customer",
                    Reward.expires_at.isnot(None),
                    Reward.expires_at > now,
                    Reward.expires_at <= horizon,
                )
            )
        ).all()
        if not rows:
            raise HTTPException(status_code=400, detail="No live rewards to remind about")

        prefs_rows = (
            await db.execute(
                select(UserNotificationPreference).where(
                    UserNotificationPreference.user_id.in_([u.id for _, u in rows])
                )
            )
        ).scalars().all()
        prefs = {p.user_id: p for p in prefs_rows}

        sms_sent = sms_skipped = 0
        for reward, user in rows:
            p = prefs.get(user.id)
            consent = bool(p and p.sms_marketing_opt_in)
            if should_send_reward_sms(consent, mailing, REMINDER_SMS_TEMPLATE, user.phone):
                sms_body = render_reward_sms(
                    REMINDER_SMS_TEMPLATE,
                    restaurant_name,
                    reward.code,
                    ordering_url,
                    mailing,
                )
                queued_sms.append((user.phone, sms_body))
                db.add(
                    Notification(
                        sender_id=current_user.id,
                        recipient_id=user.id,
                        title="Reward expiring reminder",
                        body=sms_body,
                        channel="sms",
                        message_type="marketing",
                        status="sent",
                    )
                )
                sms_sent += 1
            else:
                sms_skipped += 1

        action = InsightAction(
            insight_key=body.insight_key,
            action_type=body.action_type,
            source_code=source_code,
            reward_template_id=None,
            acted_by=current_user.id,
            targeted_count=len(rows),
            rewards_issued=0,
            already_had=0,
            sms_sent=sms_sent,
            sms_skipped=sms_skipped,
            params={"reward_ids": [r.id for r, _ in rows]},
        )

    db.add(action)
    await db.commit()

    # Only text once the rewards and the log row are durable — send_sms swallows
    # provider errors, so delivery failures can't break the response either.
    for phone, sms_body in queued_sms:
        sms_service.send_sms(phone, sms_body)

    return {
        "data": {
            "action_id": action.id,
            "targeted": action.targeted_count,
            "rewards_issued": action.rewards_issued,
            "already_had": action.already_had,
            "sms_sent": action.sms_sent,
            "sms_skipped": action.sms_skipped,
        }
    }
