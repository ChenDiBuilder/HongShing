"""Unit tests for the decisioning segment math.

These lock in the boundaries the recommendation cards depend on. Each rule is
deterministic; a customer a day inside a threshold must classify differently
from one a day outside it.
"""
from datetime import date, datetime, timedelta, timezone

from app.services.decisioning import (
    CustomerHistory,
    cadence_days,
    campaign_leaks,
    classify_customers,
    estimated_return_cents,
    lapse_assessment,
    slow_day_assessment,
    template_verdicts,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def _times(days_ago: list[float]) -> list[datetime]:
    return [NOW - timedelta(days=d) for d in days_ago]


def _customer(uid: str, days_ago: list[float], spent: int = 10_000) -> CustomerHistory:
    return CustomerHistory(
        user_id=uid, name=uid, phone=f"+1416555{uid[-4:].zfill(4)}",
        order_times=_times(days_ago), total_spent_cents=spent,
    )


class TestCadence:
    def test_median_gap(self):
        assert cadence_days(_times([14, 7, 0])) == 7.0

    def test_unsorted_input(self):
        assert cadence_days(_times([0, 14, 7])) == 7.0

    def test_needs_two_orders(self):
        assert cadence_days(_times([3])) is None


class TestLapsed:
    def test_weekly_regular_gone_12_days_is_not_lapsed(self):
        # Cadence 7 → threshold max(14, 14) = 14. Gone 12 ≤ 14: still fine.
        a = lapse_assessment(_times([26, 19, 12]), NOW)
        assert a["lapsed"] is False

    def test_weekly_regular_gone_15_days_is_lapsed(self):
        a = lapse_assessment(_times([29, 22, 15]), NOW)
        assert a["lapsed"] is True
        assert a["cadence_days"] == 7.0
        assert a["threshold_days"] == 14.0

    def test_biweekly_regular_uses_their_own_rhythm(self):
        # Cadence 10 → threshold 20. Gone 19: no. Gone 21: yes.
        assert lapse_assessment(_times([39, 29, 19]), NOW)["lapsed"] is False
        assert lapse_assessment(_times([41, 31, 21]), NOW)["lapsed"] is True

    def test_daily_regular_protected_by_floor(self):
        # Cadence 1 → 2× is 2 days, but the 14-day floor stops weekend nagging.
        assert lapse_assessment(_times([7, 6, 5]), NOW)["lapsed"] is False

    def test_floor_is_pinned_at_fourteen_days(self):
        # Cadence 2 → 2× is 4; only the floor protects days 5-14. Gone 13 must
        # be safe and gone 15 must trip, or the floor has silently moved.
        assert lapse_assessment(_times([17, 15, 13]), NOW)["lapsed"] is False
        assert lapse_assessment(_times([19, 17, 15]), NOW)["lapsed"] is True

    def test_cold_customers_age_out(self):
        # Gone 130 days: past the ceiling, not "win-back" material anymore.
        assert lapse_assessment(_times([144, 137, 130]), NOW)["lapsed"] is False

    def test_two_orders_is_not_a_regular(self):
        assert lapse_assessment(_times([40, 30]), NOW) is None


class TestClassification:
    def test_one_and_done_window_edges(self):
        segments = classify_customers(
            [
                _customer("too-fresh", [10]),
                _customer("in-window", [20]),
                _customer("too-cold", [61]),
            ],
            NOW,
        )
        assert [p["user_id"] for p in segments["one_and_done"]] == ["in-window"]

    def test_lapsed_never_double_listed_as_vip(self):
        big_lapsed = _customer("whale-gone", [40, 33, 26], spent=90_000)
        active_vip = _customer("vivian", [15, 8, 1], spent=50_000)
        segments = classify_customers([big_lapsed, active_vip], NOW)
        assert [p["user_id"] for p in segments["lapsed"]] == ["whale-gone"]
        assert [p["user_id"] for p in segments["vips"]] == ["vivian"]

    def test_lapsed_sorted_by_lifetime_spend(self):
        a = _customer("small", [40, 33, 26], spent=5_000)
        b = _customer("large", [40, 33, 26], spent=50_000)
        segments = classify_customers([a, b], NOW)
        assert [p["user_id"] for p in segments["lapsed"]] == ["large", "small"]

    def test_vip_needs_three_orders(self):
        two_timer = _customer("pair", [10, 3], spent=99_000)
        assert classify_customers([two_timer], NOW)["vips"] == []

    def test_cold_whale_is_not_a_vip(self):
        # Ten orders, big spend, gone 300 days: past the win-back ceiling so
        # not lapsed — but "still comes regularly" must not apply either.
        dead = _customer(
            "ghost", [363, 356, 349, 342, 335, 328, 321, 314, 307, 300], spent=200_000
        )
        segments = classify_customers([dead], NOW)
        assert segments["vips"] == []
        assert segments["lapsed"] == []

    def test_impact_is_a_third_of_average_tickets(self):
        # Two lapsed regulars averaging $30 and $60 → (3000+6000)/3 = $30.
        a = _customer("a", [40, 33, 26], spent=9_000)   # avg 3000
        b = _customer("b", [40, 33, 26], spent=18_000)  # avg 6000
        people = classify_customers([a, b], NOW)["lapsed"]
        assert estimated_return_cents(people) == 3_000


class TestSlowDay:
    def _weeks(self, n: int, weekday_revenue: dict[int, int]) -> list[tuple[date, int]]:
        """n weeks of daily revenue, keyed by weekday (0=Mon)."""
        start = date(2026, 6, 1)  # a Monday
        out = []
        for week in range(n):
            for wd, revenue in weekday_revenue.items():
                out.append((start + timedelta(days=week * 7 + wd), revenue))
        return out

    def test_insufficient_span_is_locked_not_wrong(self):
        result = slow_day_assessment(self._weeks(2, {0: 100, 1: 100, 2: 100, 3: 100, 4: 100}))
        assert result["status"] == "insufficient"

    def test_fires_on_a_genuinely_slow_day(self):
        # Tuesdays at 30% of everyone else across 5 weeks.
        revenue = {0: 100_000, 1: 30_000, 2: 100_000, 3: 100_000, 4: 100_000}
        result = slow_day_assessment(self._weeks(5, revenue))
        assert result["status"] == "ok"
        assert result["fires"] is True
        assert result["slowest"]["weekday"] == "Tuesday"

    def test_mildly_soft_day_does_not_fire(self):
        # 70% of median is soft, not card-worthy.
        revenue = {0: 100_000, 1: 70_000, 2: 100_000, 3: 100_000, 4: 100_000}
        result = slow_day_assessment(self._weeks(5, revenue))
        assert result["fires"] is False

    def test_closed_day_is_excluded_not_slow(self):
        # One stray Monday order in 5 weeks — that's a closed day, not a slow one.
        rows = self._weeks(5, {1: 100_000, 2: 100_000, 3: 100_000, 4: 100_000, 5: 100_000})
        rows.append((date(2026, 6, 8), 4_000))  # a single Monday
        result = slow_day_assessment(rows)
        assert result["status"] == "ok"
        assert all(w["weekday"] != "Monday" for w in result["weekdays"])


class TestTemplateVerdicts:
    def _row(self, tid, issued, redeemed, name="10% off"):
        return {
            "template_id": tid, "name": name, "reward_type": "percent",
            "reward_value": 10, "issued": issued, "redeemed": redeemed,
            "revenue_cents": redeemed * 4_000,
        }

    def test_dud_and_winner(self):
        v = template_verdicts([self._row("a", 40, 2), self._row("b", 40, 14)])
        assert v["dud"]["template_id"] == "a"
        assert v["winner"]["template_id"] == "b"

    def test_small_samples_are_ignored(self):
        v = template_verdicts([self._row("a", 9, 0)])
        assert v == {"winner": None, "dud": None}

    def test_single_qualified_template_yields_winner_only(self):
        # 30% redemption clears the winner bar and is nowhere near dud range.
        v = template_verdicts([self._row("a", 40, 12)])
        assert v["winner"]["template_id"] == "a"
        assert v["dud"] is None


class TestCampaignLeaks:
    def _row(self, sc, scans, signups):
        return {"source_code": sc, "campaign_name": sc, "scans": scans, "signups": signups}

    def test_leak_detected_against_best(self):
        leak = campaign_leaks([self._row("counter", 100, 30), self._row("bag", 100, 5)])
        assert leak["leak"]["source_code"] == "bag"
        assert leak["best"]["source_code"] == "counter"

    def test_no_leak_when_rates_comparable(self):
        assert campaign_leaks([self._row("a", 100, 30), self._row("b", 100, 20)]) is None

    def test_needs_two_qualified_sources(self):
        assert campaign_leaks([self._row("a", 100, 30), self._row("b", 10, 0)]) is None
