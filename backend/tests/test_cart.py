"""Cart and reward uniqueness / race-safety (SCRUM-72).

These lock in the DB-level guards: one active cart per user, one line per
(cart, menu item) with quantity-merging upserts, and atomic single-redemption.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models import Cart, CartItem, RestaurantSettings, Reward, RewardTemplate
from app.services.auth_service import create_access_token

ITEM_A = "11111111-1111-1111-1111-111111111111"
ITEM_B = "22222222-2222-2222-2222-222222222222"


def _auth_customer(client, user):
    client.cookies.set("access_token", create_access_token(user.id, "customer"))


def _auth_owner(client, user):
    client.cookies.set("admin_access_token", create_access_token(user.id, "owner"))


async def _active_cart_count(db, user_id) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(Cart)
        .where(Cart.user_id == user_id, Cart.is_active == True)  # noqa: E712
    )


class TestCartUniqueness:
    async def test_repeat_add_merges_into_one_line(self, client, db_session, customer_user):
        """Adding the same item twice merges quantity into a single line in a
        single active cart (no duplicate carts, no duplicate lines)."""
        _auth_customer(client, customer_user)
        base = {"menu_item_id": ITEM_A, "name": "Kung Pao", "price_cents": 1499}

        r1 = await client.post("/api/cart/items", json={**base, "quantity": 1})
        r2 = await client.post("/api/cart/items", json={**base, "quantity": 2})
        assert r1.status_code == 200 and r2.status_code == 200

        assert await _active_cart_count(db_session, customer_user.id) == 1
        items = (
            await db_session.execute(
                select(CartItem)
                .join(Cart, CartItem.cart_id == Cart.id)
                .where(Cart.user_id == customer_user.id)
            )
        ).scalars().all()
        assert len(items) == 1
        assert items[0].quantity == 3

    async def test_distinct_items_share_one_cart(self, client, db_session, customer_user):
        _auth_customer(client, customer_user)
        await client.post("/api/cart/items", json={"menu_item_id": ITEM_A, "name": "A", "price_cents": 100, "quantity": 1})
        await client.post("/api/cart/items", json={"menu_item_id": ITEM_B, "name": "B", "price_cents": 200, "quantity": 1})

        assert await _active_cart_count(db_session, customer_user.id) == 1
        n_items = (
            await db_session.execute(
                select(func.count())
                .select_from(CartItem)
                .join(Cart, CartItem.cart_id == Cart.id)
                .where(Cart.user_id == customer_user.id)
            )
        ).scalar()
        assert n_items == 2


class TestRewardRedemption:
    async def test_reward_cannot_be_double_redeemed(self, client, db_session, owner_user, customer_user):
        template = RewardTemplate(name="$5 Off", code_prefix="HS", reward_type="fixed", reward_value=500)
        db_session.add(template)
        await db_session.flush()
        reward = Reward(
            user_id=customer_user.id,
            reward_template_id=template.id,
            code="HS-TEST01",
            status="issued",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(reward)
        await db_session.flush()

        _auth_owner(client, owner_user)
        first = await client.patch(f"/api/admin/rewards/{reward.id}/redeem")
        second = await client.patch(f"/api/admin/rewards/{reward.id}/redeem")

        assert first.status_code == 200
        assert second.status_code == 400  # already redeemed — not redeemed twice


class TestRewardBranding:
    async def test_claim_uses_template_prefix_and_clone_domain(self, client, db_session, customer_user):
        """A clone's reward code uses its own prefix, and the short link uses its
        own public_domain — not 'HS-' / hongshing.ca (SCRUM-58/59)."""
        template = RewardTemplate(name="Yum Reward", code_prefix="YUM", reward_type="fixed", reward_value=500)
        db_session.add(template)
        await db_session.flush()
        db_session.add(RestaurantSettings(
            restaurant_name="Yum Kitchen",
            default_reward_template_id=template.id,
            public_domain="https://yum.test",
        ))
        await db_session.flush()

        _auth_customer(client, customer_user)
        r = await client.post("/api/rewards/claim", json={})
        assert r.status_code == 200
        data = r.json()
        assert data["reward"]["code"].startswith("YUM-")
        assert "hongshing" not in (data.get("short_link") or "")
        assert (data.get("short_link") or "").startswith("https://yum.test/r/")
