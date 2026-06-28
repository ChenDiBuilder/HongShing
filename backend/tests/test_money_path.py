"""Money-path tests for reward-discounted checkout (PRD-12 / SCRUM-75 + SCRUM-76).

Drives the real /api/cart/items -> /api/cart/checkout flow and asserts the
subtotal / discount / tax / total breakdown, currency passthrough, the
percent-vs-fixed discount math, and double-spend prevention.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import RestaurantSettings, Reward, RewardTemplate
from app.services.auth_service import create_access_token

ITEM_A = "11111111-1111-1111-1111-111111111111"
ITEM_B = "22222222-2222-2222-2222-222222222222"


def _auth(client, user):
    client.cookies.set("access_token", create_access_token(user.id, "customer"))


async def _add(client, menu_item_id, name, price_cents, qty=1):
    return await client.post(
        "/api/cart/items",
        json={"menu_item_id": menu_item_id, "name": name, "price_cents": price_cents, "quantity": qty},
    )


async def _settings(db, **kw):
    db.add(RestaurantSettings(id="00000000-0000-0000-0000-000000000001",
                              restaurant_name="T", primary_color="#000000", **kw))
    await db.flush()


async def _issue_reward(db, user, reward_type, value, *, expires_days=30, min_order=None):
    t = RewardTemplate(name="R", code_prefix="T", reward_type=reward_type,
                       reward_value=value, min_order_cents=min_order)
    db.add(t)
    await db.flush()
    r = Reward(user_id=user.id, reward_template_id=t.id, code="T-ABC123", status="issued",
               expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days))
    db.add(r)
    await db.flush()
    return r


class TestMoneyPath:
    async def test_no_reward_no_tax(self, client, db_session, customer_user):
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 500, 2)  # 1000
        await _add(client, ITEM_B, "B", 250, 1)  # 250
        d = (await client.post("/api/cart/checkout")).json()
        assert d["subtotal_cents"] == 1250
        assert d["discount_cents"] == 0
        assert d["tax_cents"] == 0          # no settings row -> no tax
        assert d["total_cents"] == 1250
        assert d["currency_symbol"] == "$"  # neutral default

    async def test_tax_applied_on_discounted_subtotal(self, client, db_session, customer_user):
        await _settings(db_session, tax_rate=0.13, currency_symbol="$")
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 1000, 1)
        d = (await client.post("/api/cart/checkout")).json()
        assert d["subtotal_cents"] == 1000
        assert d["tax_cents"] == 130        # round(1000 * 0.13)
        assert d["total_cents"] == 1130

    async def test_currency_symbol_passthrough(self, client, db_session, customer_user):
        await _settings(db_session, currency_symbol="£")
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 999, 1)
        d = (await client.post("/api/cart/checkout")).json()
        assert d["currency_symbol"] == "£"

    async def test_percentage_reward_applied_before_tax(self, client, db_session, customer_user):
        await _settings(db_session, tax_rate=0.13)
        reward = await _issue_reward(db_session, customer_user, "percentage", 20)
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 999, 1)
        d = (await client.post("/api/cart/checkout", json={"reward_id": reward.id})).json()
        # 20% of 999 == 199 (floor), tax on the discounted 800.
        assert d["discount_cents"] == 199
        assert d["tax_cents"] == round((999 - 199) * 0.13)   # 104
        assert d["total_cents"] == 999 - 199 + d["tax_cents"]
        assert d["reward_code"] == reward.code
        row = (await db_session.execute(select(Reward).where(Reward.id == reward.id))).scalar_one()
        assert row.status == "redeemed" and row.redemption_source == "checkout"

    async def test_percent_alias_also_discounts(self, client, db_session, customer_user):
        # The Restaurant Profile / seeder store "percent"; it must discount too.
        await _issue_reward(db_session, customer_user, "percent", 10)
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 1000, 1)
        reward_id = (await db_session.execute(select(Reward.id))).scalar_one()
        d = (await client.post("/api/cart/checkout", json={"reward_id": reward_id})).json()
        assert d["discount_cents"] == 100

    async def test_fixed_reward_clamped_to_subtotal(self, client, db_session, customer_user):
        await _issue_reward(db_session, customer_user, "fixed", 1500)
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 800, 1)
        reward_id = (await db_session.execute(select(Reward.id))).scalar_one()
        d = (await client.post("/api/cart/checkout", json={"reward_id": reward_id})).json()
        assert d["discount_cents"] == 800     # capped, never negative total
        assert d["total_cents"] == 0

    async def test_no_double_spend_at_checkout(self, client, db_session, customer_user):
        reward = await _issue_reward(db_session, customer_user, "fixed", 300)
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 1000, 1)
        first = (await client.post("/api/cart/checkout", json={"reward_id": reward.id})).json()
        assert first["discount_cents"] == 300
        # New cart, re-present the already-redeemed reward — no discount this time.
        await _add(client, ITEM_B, "B", 1000, 1)
        second = (await client.post("/api/cart/checkout", json={"reward_id": reward.id})).json()
        assert second["discount_cents"] == 0
        assert second["total_cents"] == 1000

    async def test_below_min_order_no_discount(self, client, db_session, customer_user):
        reward = await _issue_reward(db_session, customer_user, "fixed", 500, min_order=5000)
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 1000, 1)
        d = (await client.post("/api/cart/checkout", json={"reward_id": reward.id})).json()
        assert d["discount_cents"] == 0
        # The reward is NOT consumed when it doesn't apply.
        row = (await db_session.execute(select(Reward).where(Reward.id == reward.id))).scalar_one()
        assert row.status == "issued"

    async def test_expired_reward_no_discount(self, client, db_session, customer_user):
        reward = await _issue_reward(db_session, customer_user, "fixed", 500, expires_days=-1)
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 1000, 1)
        d = (await client.post("/api/cart/checkout", json={"reward_id": reward.id})).json()
        assert d["discount_cents"] == 0

    async def test_other_users_reward_rejected(self, client, db_session, customer_user, owner_user):
        # A reward belonging to another user must not discount the caller's order.
        reward = await _issue_reward(db_session, owner_user, "fixed", 500)
        _auth(client, customer_user)
        await _add(client, ITEM_A, "A", 1000, 1)
        d = (await client.post("/api/cart/checkout", json={"reward_id": reward.id})).json()
        assert d["discount_cents"] == 0


class TestMockSeedConsistency:
    async def test_seeded_orders_keep_subtotal_eq_total(self, client, db_session, owner_user):
        """Mock-seed orders carry no reward/tax, so subtotal_cents must equal a
        nonzero total_cents (the INSERT writes 0 before the item loop; the post-loop
        UPDATE must fix BOTH columns)."""
        from app.models import Order

        client.cookies.set("admin_access_token", create_access_token(owner_user.id, "owner"))
        r = await client.post("/api/admin/seed-mock-data")
        assert r.status_code == 200

        orders = (await db_session.execute(select(Order))).scalars().all()
        assert orders, "seed should create mock orders"
        for o in orders:
            assert o.subtotal_cents == o.total_cents
            assert o.subtotal_cents > 0
