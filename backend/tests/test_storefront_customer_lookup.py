"""Front Desk customer lookup — the staff tablet's "who is calling" surface.

Staff type a phone number however it was written down and get back everything
the restaurant knows about that person. These lock in the three behaviours the
demo depends on: messy input still finds the customer, "the usual" reflects
what they actually buy, and a stranger is a normal answer rather than an error.
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models import Device, Order, OrderItem, Reward, RewardTemplate, User
from app.services.auth_service import create_access_token, hash_otp

LOOKUP = "/api/storefront/customer-lookup"


def _auth_device(client, device: Device) -> None:
    client.cookies.set(
        "storefront_token",
        create_access_token(device.id, "device", token_type="device_access"),
    )


@pytest_asyncio.fixture
async def device(db_session) -> Device:
    d = Device(name="Front Counter Tablet", pin_hash=hash_otp("4321"), is_active=True)
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest_asyncio.fixture
async def regular(db_session) -> User:
    """A customer with a clear standing order and one live reward."""
    u = User(phone="+16475551234", name="Amy Chen", role="customer")
    db_session.add(u)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    # Three visits. General Tao on every one, fried rice on two.
    basket = [
        [("General Tao Lobster", 4500, 1), ("XO Seafood Fried Rice", 2200, 1)],
        [("General Tao Lobster", 4500, 1), ("XO Seafood Fried Rice", 2200, 1)],
        [("General Tao Lobster", 4500, 1)],
    ]
    for i, items in enumerate(basket):
        sub = sum(p * q for _, p, q in items)
        o = Order(
            user_id=u.id,
            subtotal_cents=sub,
            discount_cents=0,
            tax_cents=0,
            total_cents=sub,
            item_count=sum(q for _, _, q in items),
            status="completed" if i else "preparing",
            created_at=now - timedelta(days=i * 7),
        )
        db_session.add(o)
        await db_session.flush()
        for name, price, qty in items:
            db_session.add(
                OrderItem(order_id=o.id, name=name, price_cents=price, quantity=qty)
            )

    tmpl = RewardTemplate(name="10% off", valid_days=30)
    db_session.add(tmpl)
    await db_session.flush()
    db_session.add(
        Reward(
            user_id=u.id,
            reward_template_id=tmpl.id,
            code="HS-TEST-10",
            status="issued",
            expires_at=now + timedelta(days=9),
        )
    )
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.mark.asyncio
async def test_lookup_requires_a_device(client, regular):
    """No device cookie, no customer data. Staff surfaces are never public."""
    r = await client.get(LOOKUP, params={"phone": "6475551234"})
    assert r.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "typed",
    ["6475551234", "647-555-1234", "(647) 555 1234", "+16475551234", "16475551234"],
)
async def test_finds_the_customer_however_it_was_written_down(
    client, device, regular, typed
):
    """Staff copy numbers off a slip. Every plausible format must resolve."""
    _auth_device(client, device)
    r = await client.get(LOOKUP, params={"phone": typed})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["found"] is True
    assert data["phone"] == "+16475551234"
    assert data["name"] == "Amy Chen"


@pytest.mark.asyncio
async def test_the_usual_is_what_they_actually_buy(client, device, regular):
    """Ranked by total quantity across all visits, not by most recent order."""
    _auth_device(client, device)
    r = await client.get(LOOKUP, params={"phone": "6475551234"})
    usual = r.json()["data"]["usual"]

    assert usual[0]["name"] == "General Tao Lobster"
    assert usual[0]["quantity"] == 3
    assert usual[0]["ordered_in"] == 3
    assert usual[1]["name"] == "XO Seafood Fried Rice"
    assert usual[1]["quantity"] == 2


@pytest.mark.asyncio
async def test_visit_and_spend_totals(client, device, regular):
    _auth_device(client, device)
    data = (await client.get(LOOKUP, params={"phone": "6475551234"})).json()["data"]

    assert data["visits"] == 3
    assert data["total_spent_cents"] == 6700 + 6700 + 4500
    assert data["last_order_at"] is not None


@pytest.mark.asyncio
async def test_only_live_rewards_are_offered(client, device, regular, db_session):
    """Staff must never be told to honour something already spent or expired."""
    _auth_device(client, device)
    data = (await client.get(LOOKUP, params={"phone": "6475551234"})).json()["data"]
    assert data["rewards_live_count"] == 1

    reward = (
        await db_session.execute(select(Reward).where(Reward.user_id == regular.id))
    ).scalar_one()
    reward.status = "redeemed"
    await db_session.commit()

    data = (await client.get(LOOKUP, params={"phone": "6475551234"})).json()["data"]
    assert data["rewards_live_count"] == 0
    assert data["rewards_live"] == []


@pytest.mark.asyncio
async def test_expired_reward_is_not_live(client, device, regular, db_session):
    _auth_device(client, device)
    reward = (
        await db_session.execute(select(Reward).where(Reward.user_id == regular.id))
    ).scalar_one()
    reward.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    data = (await client.get(LOOKUP, params={"phone": "6475551234"})).json()["data"]
    assert data["rewards_live_count"] == 0


@pytest.mark.asyncio
async def test_open_orders_are_separated_from_history(client, device, regular):
    """Staff need to know what is on the pass right now, not just what they've had."""
    _auth_device(client, device)
    data = (await client.get(LOOKUP, params={"phone": "6475551234"})).json()["data"]

    assert len(data["open_orders"]) == 1
    assert data["open_orders"][0]["status"] == "preparing"
    assert len(data["recent_orders"]) == 3


@pytest.mark.asyncio
async def test_unknown_caller_is_a_normal_answer(client, device):
    """Most callers are strangers early on. Not found is not an error, and the
    number still comes back normalized so staff can read it back to confirm."""
    _auth_device(client, device)
    r = await client.get(LOOKUP, params={"phone": "416-977-3338"})

    assert r.status_code == 200
    data = r.json()["data"]
    assert data["found"] is False
    assert data["phone"] == "+14169773338"


@pytest.mark.asyncio
async def test_unusable_number_says_why(client, device):
    _auth_device(client, device)
    data = (await client.get(LOOKUP, params={"phone": "12"})).json()["data"]

    assert data["found"] is False
    assert data["phone"] is None
    assert data["reason"] == "not_a_north_american_number"
