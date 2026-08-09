"""Tests for the pilot goal-metrics endpoint (SCRUM-242)."""

from datetime import datetime, timedelta, timezone

from app.models import InsightAction, Order, Reward, RewardTemplate, SignupEvent, User
from app.services.auth_service import create_access_token


def _order(user_id: str, cents: int, days_ago: float, reward_id: str | None = None, status: str = "picked_up") -> Order:
    return Order(
        user_id=user_id,
        subtotal_cents=cents,
        discount_cents=0,
        tax_cents=0,
        total_cents=cents,
        item_count=1,
        status=status,
        reward_id=reward_id,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )


class TestGoalMetrics:
    async def test_empty_db_returns_zeroes(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/analytics/goals")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["phones_captured"] == 0
        assert data["orders"] == 0
        assert data["capture_per_100_orders"] is None
        assert data["winback_revenue_cents"] == 0
        assert data["winback_redemptions"] == 0

    async def test_capture_rate_and_winback_attribution(self, client, owner_user, db_session):
        now = datetime.now(timezone.utc)
        cust = User(phone="+14035550042", name="Goal Cust", role="customer")
        db_session.add(cust)
        await db_session.flush()

        # capture: one signup + two orders in-window -> 50 per 100 orders
        db_session.add(
            SignupEvent(user_id=cust.id, phone=cust.phone, created_at=now - timedelta(days=3))
        )
        db_session.add(_order(cust.id, 2_000, 2.0))

        # win-back: offer action minted a dec- reward; its redemption order counts
        template = RewardTemplate(name="10% back", reward_type="percent", reward_value=10)
        db_session.add(template)
        await db_session.flush()
        action = InsightAction(
            insight_key="lapsed_regulars",
            action_type="send_offer",
            source_code="dec-goal0001",
            acted_by=owner_user.id,
            targeted_count=1,
            rewards_issued=1,
            created_at=now - timedelta(days=10),
        )
        db_session.add(action)
        reward = Reward(
            user_id=cust.id,
            reward_template_id=template.id,
            code="HS-GOAL1",
            source_code="dec-goal0001",
            status="redeemed",
            redeemed_at=now - timedelta(days=5),
        )
        db_session.add(reward)
        await db_session.flush()
        db_session.add(_order(cust.id, 5_400, 5.0, reward_id=reward.id))

        # outside the 30d window: must not count anywhere
        db_session.add(_order(cust.id, 9_900, 40.0))
        await db_session.commit()

        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/analytics/goals?days=30")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["phones_captured"] == 1
        assert data["orders"] == 2
        assert data["capture_per_100_orders"] == 50.0
        assert data["winback_redemptions"] == 1
        assert data["winback_revenue_cents"] == 5_400
