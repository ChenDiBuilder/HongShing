"""Decisioning — turn order history into ranked, actionable recommendations.

This is the layer that makes the data worth paying for. Analytics counts what
happened; this module decides what to do about it. Every rule here is
deterministic and explainable: an owner should be able to read the "why" on a
card and check the math on a napkin.

Pure functions over plain data — the DB assembly lives in the route so these
boundaries can be unit-tested precisely (a regular who comes every 9 days and
has been gone 12 is NOT lapsed; gone 19, they are).
"""
from dataclasses import dataclass, field
from datetime import date, datetime

# --- Lapsed regulars -------------------------------------------------------
# A regular has a rhythm; lapsed means the rhythm broke. Twice their own median
# gap is long enough to mean "something changed" without nagging someone who is
# merely a few days late. The 14-day floor stops a lunch-daily regular from
# triggering after one quiet weekend.
LAPSED_MIN_ORDERS = 3
LAPSED_CADENCE_MULTIPLIER = 2.0
LAPSED_FLOOR_DAYS = 14.0
# Beyond this we stop calling it "win-back" — the relationship is cold and a
# routine 10%-off text reads as spam. Keep the list actionable, not archaeological.
LAPSED_CEILING_DAYS = 120.0

# --- One-and-done ----------------------------------------------------------
# One visit, then silence. Under 14 days it's too early to conclude anything;
# past 60 the trail is cold (see ceiling rationale above).
ONE_AND_DONE_MIN_DAYS = 14.0
ONE_AND_DONE_MAX_DAYS = 60.0

# --- VIPs -------------------------------------------------------------------
VIP_MIN_ORDERS = 3
VIP_LIMIT = 5

# --- Expiring rewards -------------------------------------------------------
EXPIRING_WINDOW_DAYS = 7

# --- Slow day ---------------------------------------------------------------
# Weekday comparison needs enough weeks that one bad Tuesday isn't a verdict.
SLOW_DAY_WINDOW_DAYS = 56
SLOW_DAY_MIN_SPAN_DAYS = 28
SLOW_DAY_MIN_ACTIVE_DATES = 2  # a weekday with fewer order-dates is treated as closed
SLOW_DAY_MIN_WEEKDAYS = 4
SLOW_DAY_THRESHOLD = 0.6  # slowest must be under 60% of the median weekday

# --- Reward template performance ---------------------------------------------
TEMPLATE_WINDOW_DAYS = 90
TEMPLATE_MIN_ISSUED = 10
TEMPLATE_DUD_RATE = 0.10
TEMPLATE_WINNER_RATE = 0.25

# --- Campaign funnel ----------------------------------------------------------
CAMPAIGN_WINDOW_DAYS = 60
CAMPAIGN_MIN_SCANS = 30
CAMPAIGN_LEAK_FACTOR = 0.5  # under half the best placement's conversion

# Impact estimates assume a third of the targeted people return once. Shown to
# the owner as exactly that — an assumption, not a promise.
RETURN_ASSUMPTION_DENOMINATOR = 3

WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


@dataclass
class CustomerHistory:
    """One customer's order timeline, oldest first."""

    user_id: str
    name: str | None
    phone: str | None
    order_times: list[datetime] = field(default_factory=list)
    total_spent_cents: int = 0

    @property
    def visits(self) -> int:
        return len(self.order_times)

    @property
    def avg_order_cents(self) -> int:
        return self.total_spent_cents // self.visits if self.visits else 0


def median(values: list[float]) -> float:
    """Plain median. Raises on empty input — callers gate on sample size."""
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def cadence_days(order_times: list[datetime]) -> float | None:
    """Median gap between consecutive orders, in days. None below 2 orders."""
    if len(order_times) < 2:
        return None
    times = sorted(order_times)
    gaps = [
        (b - a).total_seconds() / 86400 for a, b in zip(times, times[1:])
    ]
    return median(gaps)


def days_since(last: datetime, now: datetime) -> float:
    return (now - last).total_seconds() / 86400


def lapse_assessment(order_times: list[datetime], now: datetime) -> dict | None:
    """Is this regular overdue by their own rhythm?

    Returns None unless the customer qualifies as a regular (>= LAPSED_MIN_ORDERS).
    Otherwise a dict with the numbers the card shows: their cadence, how long
    they've been gone, and the threshold that tripped (or didn't).
    """
    if len(order_times) < LAPSED_MIN_ORDERS:
        return None
    cadence = cadence_days(order_times)
    gone = days_since(max(order_times), now)
    threshold = max(cadence * LAPSED_CADENCE_MULTIPLIER, LAPSED_FLOOR_DAYS)
    return {
        "cadence_days": cadence,
        "days_since_last": gone,
        "threshold_days": threshold,
        "lapsed": threshold < gone <= LAPSED_CEILING_DAYS,
    }


def classify_customers(
    histories: list[CustomerHistory], now: datetime
) -> dict[str, list[dict]]:
    """Split customers into the three people-segments the cards act on.

    Segments are disjoint: a lapsed regular is never also listed as a VIP —
    lapsed is the more urgent fact, and the lapsed list sorts by lifetime spend
    so the biggest names surface first anyway.
    """
    lapsed: list[dict] = []
    one_and_done: list[dict] = []
    vip_pool: list[CustomerHistory] = []

    for h in histories:
        if not h.order_times:
            continue
        gone = days_since(max(h.order_times), now)

        if h.visits == 1:
            if ONE_AND_DONE_MIN_DAYS <= gone <= ONE_AND_DONE_MAX_DAYS:
                one_and_done.append(_person(h, gone, None))
            continue

        assessment = lapse_assessment(h.order_times, now)
        if assessment and assessment["lapsed"]:
            lapsed.append(_person(h, gone, assessment["cadence_days"]))
        elif (
            assessment
            and h.visits >= VIP_MIN_ORDERS
            and gone <= assessment["threshold_days"]
        ):
            # VIP means "still comes regularly" — inside their own rhythm. A
            # big spender gone past the win-back ceiling is cold, not a VIP.
            vip_pool.append(h)

    lapsed.sort(key=lambda p: -p["total_spent_cents"])
    # Freshest lapse first within equal spend would be nice, but spend is the
    # owner's instinctive ordering — keep it single-keyed and predictable.
    one_and_done.sort(key=lambda p: p["days_since_last"])

    vip_pool.sort(key=lambda h: -h.total_spent_cents)
    vips = [
        _person(h, days_since(max(h.order_times), now), cadence_days(h.order_times))
        for h in vip_pool[:VIP_LIMIT]
    ]
    return {"lapsed": lapsed, "one_and_done": one_and_done, "vips": vips}


def _person(h: CustomerHistory, gone: float, cadence: float | None) -> dict:
    return {
        "user_id": h.user_id,
        "name": h.name,
        "phone": h.phone,
        "visits": h.visits,
        "total_spent_cents": h.total_spent_cents,
        "avg_order_cents": h.avg_order_cents,
        "last_order_at": max(h.order_times).isoformat(),
        "days_since_last": round(gone, 1),
        "cadence_days": round(cadence, 1) if cadence is not None else None,
    }


def estimated_return_cents(people: list[dict]) -> int:
    """If a third of them come back once at their own average ticket."""
    return sum(p["avg_order_cents"] for p in people) // RETURN_ASSUMPTION_DENOMINATOR


def slow_day_assessment(daily_revenue: list[tuple[date, int]]) -> dict:
    """Which weekday underperforms, judged over ~8 weeks of local dates.

    Input is one row per LOCAL date with that date's revenue. Weekdays with
    fewer than SLOW_DAY_MIN_ACTIVE_DATES order-dates are treated as closed and
    excluded rather than "slow" — a restaurant dark on Mondays doesn't need a
    card telling it Mondays are quiet.
    """
    if not daily_revenue:
        return {"status": "insufficient", "have_days": 0, "need_days": SLOW_DAY_MIN_SPAN_DAYS}

    dates = [d for d, _ in daily_revenue]
    span = (max(dates) - min(dates)).days
    if span < SLOW_DAY_MIN_SPAN_DAYS:
        return {
            "status": "insufficient",
            "have_days": span,
            "need_days": SLOW_DAY_MIN_SPAN_DAYS,
        }

    by_weekday: dict[int, list[int]] = {}
    for d, revenue in daily_revenue:
        by_weekday.setdefault(d.weekday(), []).append(revenue)

    active = {
        wd: revs
        for wd, revs in by_weekday.items()
        if len(revs) >= SLOW_DAY_MIN_ACTIVE_DATES
    }
    if len(active) < SLOW_DAY_MIN_WEEKDAYS:
        return {
            "status": "insufficient",
            "have_days": span,
            "need_days": SLOW_DAY_MIN_SPAN_DAYS,
        }

    averages = {wd: sum(revs) / len(revs) for wd, revs in active.items()}
    med = median(list(averages.values()))
    slowest_wd = min(averages, key=lambda wd: averages[wd])
    slowest_avg = averages[slowest_wd]

    weekdays = [
        {
            "weekday": WEEKDAY_NAMES[wd],
            "avg_revenue_cents": int(averages[wd]),
            "active_dates": len(active[wd]),
        }
        for wd in sorted(active)
    ]
    result = {
        "status": "ok",
        "weekdays": weekdays,
        "median_avg_cents": int(med),
        "slowest": {
            "weekday": WEEKDAY_NAMES[slowest_wd],
            "avg_revenue_cents": int(slowest_avg),
            "pct_of_median": round(slowest_avg / med * 100) if med else None,
        },
        "fires": med > 0 and slowest_avg < SLOW_DAY_THRESHOLD * med,
    }
    return result


def template_verdicts(rows: list[dict]) -> dict:
    """Winner/dud among reward templates with a meaningful sample.

    Each row: {template_id, name, reward_type, reward_value, issued, redeemed,
    revenue_cents}. Rate = share of the issued cohort now redeemed.
    """
    qualified = [
        {**r, "redemption_rate": r["redeemed"] / r["issued"]}
        for r in rows
        if r["issued"] >= TEMPLATE_MIN_ISSUED
    ]
    if not qualified:
        return {"winner": None, "dud": None}
    best = max(qualified, key=lambda r: r["redemption_rate"])
    worst = min(qualified, key=lambda r: r["redemption_rate"])
    # The thresholds don't overlap (winner >= 25%, dud < 10%), so one row can
    # never earn both verdicts — no dedup needed.
    winner = best if best["redemption_rate"] >= TEMPLATE_WINNER_RATE else None
    dud = worst if worst["redemption_rate"] < TEMPLATE_DUD_RATE else None
    return {"winner": winner, "dud": dud}


def campaign_leaks(rows: list[dict]) -> dict | None:
    """A placement getting scans but not signups, judged against the best one.

    Each row: {source_code, campaign_name, scans, signups}. Only sources with a
    real sample count; the leak must convert at under half the best rate.
    """
    qualified = [
        {**r, "rate": r["signups"] / r["scans"]}
        for r in rows
        if r["scans"] >= CAMPAIGN_MIN_SCANS
    ]
    if len(qualified) < 2:
        return None
    best = max(qualified, key=lambda r: r["rate"])
    if best["rate"] <= 0:
        return None
    worst = min(qualified, key=lambda r: r["rate"])
    if worst["source_code"] == best["source_code"]:
        return None
    if worst["rate"] < CAMPAIGN_LEAK_FACTOR * best["rate"]:
        return {"best": best, "leak": worst}
    return None
