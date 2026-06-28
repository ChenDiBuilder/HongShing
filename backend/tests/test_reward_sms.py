"""Integration: CASL-gated reward-delivery SMS on claim (PRD-12 S7 / SCRUM-64)."""

from sqlalchemy import select

from app.models import RestaurantSettings, RewardTemplate, UserNotificationPreference
from app.services.auth_service import create_access_token


async def _setup(db, *, address, template):
    db.add(RestaurantSettings(
        id="00000000-0000-0000-0000-000000000001",
        restaurant_name="Pho 99", primary_color="#000000",
        business_mailing_address=address,
        reward_sms_template=template,
        external_ordering_url="https://pho99.ca/order",
    ))
    rt = RewardTemplate(name="Welcome", code_prefix="PH", reward_type="fixed", reward_value=500, valid_days=30)
    db.add(rt)
    await db.flush()
    # Point the settings' default template at the seeded reward template.
    s = (await db.execute(select(RestaurantSettings))).scalar_one()
    s.default_reward_template_id = rt.id
    await db.flush()


async def _consent(db, user, opted_in):
    db.add(UserNotificationPreference(user_id=user.id, sms_marketing_opt_in=opted_in))
    await db.flush()


def _auth(client, user):
    client.cookies.set("access_token", create_access_token(user.id, "customer"))


def _capture(monkeypatch):
    sent = []
    monkeypatch.setattr("app.routes.customer.send_sms", lambda phone, msg: sent.append((phone, msg)))
    return sent


async def test_sends_when_consent_and_address(client, db_session, customer_user, monkeypatch):
    customer_user.phone = "+14165550000"
    await _setup(db_session, address="1 King St, Toronto", template="{restaurant}: code {reward_code}")
    await _consent(db_session, customer_user, True)
    sent = _capture(monkeypatch)
    _auth(client, customer_user)

    r = await client.post("/api/rewards/claim", json={})
    assert r.status_code == 200
    assert len(sent) == 1
    phone, msg = sent[0]
    assert phone == "+14165550000"
    assert "1 King St, Toronto" in msg            # CASL footer
    assert r.json()["reward"]["code"] in msg


async def test_skips_without_consent(client, db_session, customer_user, monkeypatch):
    customer_user.phone = "+14165550000"
    await _setup(db_session, address="1 King St", template="x {reward_code}")
    await _consent(db_session, customer_user, False)
    sent = _capture(monkeypatch)
    _auth(client, customer_user)
    assert (await client.post("/api/rewards/claim", json={})).status_code == 200
    assert sent == []


async def test_skips_without_mailing_address(client, db_session, customer_user, monkeypatch):
    customer_user.phone = "+14165550000"
    await _setup(db_session, address=None, template="x {reward_code}")
    await _consent(db_session, customer_user, True)
    sent = _capture(monkeypatch)
    _auth(client, customer_user)
    assert (await client.post("/api/rewards/claim", json={})).status_code == 200
    assert sent == []


async def test_skips_without_template(client, db_session, customer_user, monkeypatch):
    customer_user.phone = "+14165550000"
    await _setup(db_session, address="1 King St", template=None)
    await _consent(db_session, customer_user, True)
    sent = _capture(monkeypatch)
    _auth(client, customer_user)
    assert (await client.post("/api/rewards/claim", json={})).status_code == 200
    assert sent == []


async def test_reclaim_does_not_resend(client, db_session, customer_user, monkeypatch):
    customer_user.phone = "+14165550000"
    await _setup(db_session, address="1 King St", template="x {reward_code}")
    await _consent(db_session, customer_user, True)
    sent = _capture(monkeypatch)
    _auth(client, customer_user)

    await client.post("/api/rewards/claim", json={})   # first claim -> sends once
    await client.post("/api/rewards/claim", json={})   # re-claim returns existing, no resend
    assert len(sent) == 1
