"""Agent ordering (Act 2) — the service behind the restaurant's MCP tools.

These pin the contract a Vela agent depends on: identity before commerce,
prices from the menu (never the caller), the checkout money path mirrored
exactly, and structured errors an agent can read aloud.
"""
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy import select

from app.models import (
    Category,
    MenuItem,
    Order,
    RestaurantSettings,
    Reward,
    RewardTemplate,
    SignupEvent,
    User,
)
from app.services.agent_orders import (
    create_agent_order,
    customer_context,
    menu_snapshot,
    order_status,
)


@pytest_asyncio.fixture
async def menu(db_session):
    cat = Category(name="Mains", slug="mains", sort_order=1)
    db_session.add(cat)
    await db_session.flush()
    items = [
        MenuItem(category_id=cat.id, name="General Tao Chicken", price_cents=1895),
        MenuItem(category_id=cat.id, name="Mapo Tofu", price_cents=1395),
        MenuItem(category_id=cat.id, name="Ghost Dish", price_cents=999, is_available=False),
    ]
    db_session.add_all(items)
    db_session.add(RestaurantSettings(restaurant_name="Hong Shing", tax_rate=0.13))
    await db_session.commit()
    return items


class TestMenu:
    async def test_menu_lists_only_available_dishes(self, db_session, menu):
        snap = await menu_snapshot(db_session)
        names = [i["name"] for c in snap["categories"] for i in c["items"]]
        assert "General Tao Chicken" in names
        assert "Ghost Dish" not in names


class TestPlaceOrder:
    async def test_identity_is_required(self, db_session, menu):
        result = await create_agent_order(
            db_session, "4165551234", "", [{"name": "Mapo Tofu", "quantity": 1}]
        )
        assert result == {"ok": False, "error": "name_required"}

    async def test_order_creates_customer_with_agent_attribution(self, db_session, menu):
        result = await create_agent_order(
            db_session,
            "416-555-9876",
            "Wei Lin",
            [{"name": "General Tao Chicken", "quantity": 2}, {"name": "Mapo Tofu", "quantity": 1}],
        )
        assert result["ok"] is True, result
        # Money: (2×1895 + 1395) = 5185 subtotal; 13% tax half-up = 674; total 5859.
        assert result["subtotal_cents"] == 5185
        assert result["tax_cents"] == 674
        assert result["total_cents"] == 5859

        user = (
            await db_session.execute(select(User).where(User.phone == "+14165559876"))
        ).scalar_one()
        assert user.name == "Wei Lin"
        signup = (
            await db_session.execute(
                select(SignupEvent).where(SignupEvent.user_id == user.id)
            )
        ).scalar_one()
        assert signup.source_code == "agent"

        order = (
            await db_session.execute(select(Order).where(Order.user_id == user.id))
        ).scalar_one()
        assert order.status == "confirmed"
        assert order.item_count == 3

    async def test_prices_come_from_the_menu_not_the_caller(self, db_session, menu):
        # A malicious/confused agent passing a price field changes nothing.
        result = await create_agent_order(
            db_session,
            "4165550001",
            "Test",
            [{"name": "Mapo Tofu", "quantity": 1, "price_cents": 1}],
        )
        assert result["ok"] is True
        assert result["subtotal_cents"] == 1395

    async def test_unknown_and_unavailable_dishes_are_named_in_the_error(
        self, db_session, menu
    ):
        result = await create_agent_order(
            db_session,
            "4165550002",
            "Test",
            [{"name": "Pizza", "quantity": 1}, {"name": "Ghost Dish", "quantity": 1}],
        )
        assert result["ok"] is False
        assert result["error"] == "items_not_on_menu"
        assert result["unknown"] == ["Pizza"]
        assert result["unavailable"] == ["Ghost Dish"]
        # And nothing was created.
        assert (
            await db_session.execute(select(User).where(User.phone == "+14165550002"))
        ).scalar_one_or_none() is None

    async def test_reward_applies_and_is_single_use(self, db_session, menu):
        u = User(phone="+14165550003", name="Regular", role="customer")
        tmpl = RewardTemplate(name="10% off", reward_type="percent", reward_value=10, valid_days=30)
        db_session.add_all([u, tmpl])
        await db_session.flush()
        db_session.add(
            Reward(
                user_id=u.id, reward_template_id=tmpl.id, code="HS-AGENT01",
                status="issued", expires_at=datetime.now(timezone.utc) + timedelta(days=5),
            )
        )
        await db_session.commit()

        first = await create_agent_order(
            db_session, "4165550003", "Regular",
            [{"name": "General Tao Chicken", "quantity": 1}], reward_code="hs-agent01",
        )
        assert first["ok"] is True
        # 1895 − 189 (10%) = 1706; tax 13% half-up = 222; total 1928.
        assert first["discount_cents"] == 189
        assert first["total_cents"] == 1928
        assert first["reward_applied"] == "HS-AGENT01"

        second = await create_agent_order(
            db_session, "4165550003", "Regular",
            [{"name": "Mapo Tofu", "quantity": 1}], reward_code="HS-AGENT01",
        )
        assert second["ok"] is False
        assert second["error"] == "reward_not_usable"

    async def test_someone_elses_reward_is_refused(self, db_session, menu):
        owner = User(phone="+14165550004", name="Owner Of Reward", role="customer")
        tmpl = RewardTemplate(name="10% off", reward_type="percent", reward_value=10)
        db_session.add_all([owner, tmpl])
        await db_session.flush()
        db_session.add(
            Reward(user_id=owner.id, reward_template_id=tmpl.id, code="HS-THEIRS1", status="issued")
        )
        await db_session.commit()

        result = await create_agent_order(
            db_session, "4165550005", "Stranger",
            [{"name": "Mapo Tofu", "quantity": 1}], reward_code="HS-THEIRS1",
        )
        assert result["ok"] is False
        assert result["error"] == "reward_not_usable"


class TestCustomerContext:
    async def test_stranger_is_a_normal_answer(self, db_session, menu):
        ctx = await customer_context(db_session, "416-555-7777")
        assert ctx == {"ok": True, "found": False, "phone": "+14165557777"}

    async def test_known_caller_gets_usual_and_live_rewards(self, db_session, menu):
        result = await create_agent_order(
            db_session, "4165550006", "Ana",
            [{"name": "Mapo Tofu", "quantity": 3}, {"name": "General Tao Chicken", "quantity": 1}],
        )
        assert result["ok"] is True
        ctx = await customer_context(db_session, "(416) 555 0006")
        assert ctx["found"] is True
        assert ctx["name"] == "Ana"
        assert ctx["visits"] == 1
        assert ctx["usual"][0] == "Mapo Tofu"

    async def test_order_status_roundtrip(self, db_session, menu):
        result = await create_agent_order(
            db_session, "4165550007", "Bo", [{"name": "Mapo Tofu", "quantity": 1}]
        )
        status = await order_status(db_session, result["order_id"])
        assert status["ok"] is True
        assert status["status"] == "confirmed"
        assert (await order_status(db_session, "00000000-0000-0000-0000-000000000000"))[
            "ok"
        ] is False


class TestTokenGate:
    # The mounted root is /mcp/ — Starlette 307s the slashless form before the
    # gate can run, so the gate is tested at the true path.

    async def test_mcp_mount_is_off_without_a_token(self, client):
        r = await client.post("/mcp/", json={})
        assert r.status_code == 404

    async def test_wrong_token_is_401_and_right_token_reaches_mcp(
        self, client, monkeypatch
    ):
        from app.config import get_settings

        monkeypatch.setattr(get_settings(), "mcp_service_token", "test-token-123")
        r = await client.post("/mcp/", json={})
        assert r.status_code == 401

        # The MCP session manager normally runs under the app lifespan, which
        # the test client skips — enter it exactly as main.py's lifespan does.
        from app.mcp_server import mcp_lifespan

        async with mcp_lifespan():
            r = await client.post(
                "/mcp/",
                json={},
                headers={"Authorization": "Bearer test-token-123"},
            )
        # Past the gate: the MCP transport answers protocol errors itself
        # (missing Accept headers etc.) — anything but 401/404 proves the gate.
        assert r.status_code not in (401, 404)
