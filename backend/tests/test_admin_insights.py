"""Integration tests for This Week — the decisioning surface.

The loop under test: GET surfaces segments with evidence → POST acts on them
(rewards + CASL-gated SMS) → the action is logged → outcomes attribute back to
the action on the next GET. Every count in the receipt must be exact; the owner
is going to read these numbers out loud.
"""
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy import select

from app.models import (
    InsightAction,
    Notification,
    Order,
    OrderItem,
    RestaurantSettings,
    Reward,
    RewardTemplate,
    User,
    UserNotificationPreference,
)
from app.services.auth_service import create_access_token, hash_password

INSIGHTS = "/api/admin/insights"
ACT = "/api/admin/insights/act"


def _admin(client, user: User, role: str | None = None) -> None:
    client.cookies.set("admin_access_token", create_access_token(user.id, role or user.role))


@pytest_asyncio.fixture
async def owner(db_session) -> User:
    u = User(
        email="owner@example.com",
        name="Owner",
        password_hash=hash_password("admin123"),
        role="owner",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def settings_row(db_session) -> RestaurantSettings:
    s = RestaurantSettings(
        restaurant_name="Hong Shing",
        business_mailing_address="195 Dundas St W, Toronto, ON",
        reward_sms_template="{restaurant}: your reward {reward_code} is ready. {ordering_url}",
        public_domain="https://order.example.com",
    )
    db_session.add(s)
    await db_session.commit()
    return s


@pytest_asyncio.fixture
async def template(db_session) -> RewardTemplate:
    t = RewardTemplate(name="10% off", reward_type="percent", reward_value=10, valid_days=30)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


async def _customer_with_orders(
    db, phone: str, name: str, days_ago: list[float], ticket_cents: int = 4_000
) -> User:
    u = User(phone=phone, name=name, role="customer")
    db.add(u)
    await db.flush()
    now = datetime.now(timezone.utc)
    for d in days_ago:
        o = Order(
            user_id=u.id,
            subtotal_cents=ticket_cents,
            discount_cents=0,
            tax_cents=0,
            total_cents=ticket_cents,
            item_count=1,
            status="completed",
            created_at=now - timedelta(days=d),
        )
        db.add(o)
        await db.flush()
        db.add(OrderItem(order_id=o.id, name="General Tao Chicken", price_cents=ticket_cents, quantity=1))
    await db.commit()
    await db.refresh(u)
    return u


class TestAccess:
    async def test_get_requires_admin(self, client):
        assert (await client.get(INSIGHTS)).status_code == 401

    async def test_staff_can_look_but_not_act(self, client, db_session, template):
        staff = User(email="staff@example.com", password_hash=hash_password("x" * 8), role="staff")
        db_session.add(staff)
        await db_session.commit()
        _admin(client, staff)
        assert (await client.get(INSIGHTS)).status_code == 200
        r = await client.post(
            ACT,
            json={
                "insight_key": "lapsed_regulars",
                "action_type": "send_offer",
                "template_id": template.id,
                "user_ids": [staff.id],
            },
        )
        assert r.status_code == 403


class TestSegments:
    async def test_cards_reflect_the_actual_history(
        self, client, db_session, owner, settings_row, template
    ):
        # Raymond: weekly regular who vanished a month ago → lapsed.
        raymond = await _customer_with_orders(
            db_session, "+14165550001", "Raymond Wu", [49, 42, 35, 28], ticket_cents=6_000
        )
        # Vivian: big spender still coming → VIP, not lapsed.
        vivian = await _customer_with_orders(
            db_session, "+14165550002", "Vivian Lam", [29, 22, 15, 8, 1], ticket_cents=9_000
        )
        # Sam: tried once three weeks ago → one-and-done.
        sam = await _customer_with_orders(db_session, "+14165550003", "Sam Park", [21])
        # Fresh first-timer: too early to conclude anything.
        await _customer_with_orders(db_session, "+14165550004", "New Person", [4])

        # Vivian holds a reward that dies in 3 days.
        now = datetime.now(timezone.utc)
        db_session.add(
            Reward(
                user_id=vivian.id,
                reward_template_id=template.id,
                code="HS-EXPIRE1",
                status="issued",
                expires_at=now + timedelta(days=3),
            )
        )
        await db_session.commit()

        _admin(client, owner)
        data = (await client.get(INSIGHTS)).json()["data"]
        cards = {c["key"]: c for c in data["cards"]}

        lapsed_people = cards["lapsed_regulars"]["evidence"]["people"]
        assert [p["name"] for p in lapsed_people] == ["Raymond Wu"]
        assert lapsed_people[0]["cadence_days"] == 7.0
        assert lapsed_people[0]["usual"] == "General Tao Chicken"

        assert [p["name"] for p in cards["one_and_done"]["evidence"]["people"]] == ["Sam Park"]
        assert [p["name"] for p in cards["vips"]["evidence"]["people"]] == ["Vivian Lam"]

        expiring = cards["expiring_rewards"]["evidence"]["rewards"]
        assert [r["code"] for r in expiring] == ["HS-EXPIRE1"]
        assert cards["expiring_rewards"]["priority"] == "act_now"

        # Not enough history for weekday analysis — locked, never guessed.
        assert cards["slow_day_locked"]["priority"] == "locked"

        assert data["coverage"]["orders"] == 11
        assert data["sms_configured"] is True

    async def test_quiet_database_has_no_people_cards(self, client, db_session, owner):
        _admin(client, owner)
        data = (await client.get(INSIGHTS)).json()["data"]
        keys = {c["key"] for c in data["cards"]}
        assert "lapsed_regulars" not in keys
        assert "one_and_done" not in keys
        assert data["coverage"]["orders"] == 0


class TestSendOffer:
    async def test_issues_rewards_texts_consented_and_logs(
        self, client, db_session, owner, settings_row, template, monkeypatch
    ):
        sent: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "app.services.sms_service.send_sms", lambda phone, body: sent.append((phone, body))
        )

        raymond = await _customer_with_orders(
            db_session, "+14165550001", "Raymond Wu", [49, 42, 35, 28]
        )
        sam = await _customer_with_orders(db_session, "+14165550003", "Sam Park", [21])

        # Raymond opted in to marketing SMS; Sam never did.
        db_session.add(UserNotificationPreference(user_id=raymond.id, sms_marketing_opt_in=True))
        # Sam already holds an issued reward on this template — must be skipped.
        db_session.add(
            Reward(
                user_id=sam.id,
                reward_template_id=template.id,
                code="HS-SAMHAS1",
                status="issued",
                expires_at=datetime.now(timezone.utc) + timedelta(days=10),
            )
        )
        await db_session.commit()

        _admin(client, owner)
        r = await client.post(
            ACT,
            json={
                "insight_key": "lapsed_regulars",
                "action_type": "send_offer",
                "template_id": template.id,
                "user_ids": [raymond.id, sam.id],
            },
        )
        assert r.status_code == 200, r.text
        result = r.json()["data"]
        assert result["targeted"] == 2
        assert result["rewards_issued"] == 1
        assert result["already_had"] == 1
        assert result["sms_sent"] == 1
        assert result["sms_skipped"] == 0

        # The new reward carries the action's attribution code.
        new_reward = (
            await db_session.execute(
                select(Reward).where(Reward.user_id == raymond.id)
            )
        ).scalar_one()
        assert new_reward.source_code.startswith("dec-")
        assert new_reward.status == "issued"

        action = (await db_session.execute(select(InsightAction))).scalar_one()
        assert action.source_code == new_reward.source_code
        assert action.insight_key == "lapsed_regulars"
        assert action.rewards_issued == 1

        # Exactly one text, to the consented number, CASL footer included.
        assert len(sent) == 1
        assert sent[0][0] == "+14165550001"
        assert "Dundas St W" in sent[0][1]
        note = (await db_session.execute(select(Notification))).scalar_one()
        assert note.recipient_id == raymond.id

    async def test_unknown_insight_is_rejected(self, client, db_session, owner, template):
        _admin(client, owner)
        r = await client.post(
            ACT,
            json={
                "insight_key": "made_up",
                "action_type": "send_offer",
                "template_id": template.id,
                "user_ids": ["00000000-0000-0000-0000-000000000009"],
            },
        )
        assert r.status_code == 400

    async def test_blast_radius_is_capped(self, client, db_session, owner, template):
        """One action can never target more than 200 people or rewards."""
        _admin(client, owner)
        fake_ids = [f"00000000-0000-0000-0000-{i:012d}" for i in range(201)]
        r = await client.post(
            ACT,
            json={
                "insight_key": "lapsed_regulars",
                "action_type": "send_offer",
                "template_id": template.id,
                "user_ids": fake_ids,
            },
        )
        assert r.status_code == 400
        r = await client.post(
            ACT,
            json={
                "insight_key": "expiring_rewards",
                "action_type": "send_reminder",
                "reward_ids": fake_ids,
            },
        )
        assert r.status_code == 400

    async def test_expired_held_reward_does_not_block_a_new_offer(
        self, client, db_session, owner, settings_row, template
    ):
        """Nothing ever flips a dead reward off status='issued', and the
        one-issued-per-template index matches on status alone — so without the
        retire-first step, exactly the people win-backs target (gone weeks,
        holding an expired signup reward) would silently get nothing while the
        receipt claimed 'already had one'."""
        lapsed = await _customer_with_orders(
            db_session, "+14165550007", "Old Regular", [49, 42, 35, 28]
        )
        stale = Reward(
            user_id=lapsed.id,
            reward_template_id=template.id,
            code="HS-STALE01",
            status="issued",
            expires_at=datetime.now(timezone.utc) - timedelta(days=15),
        )
        db_session.add(stale)
        await db_session.commit()

        _admin(client, owner)
        r = await client.post(
            ACT,
            json={
                "insight_key": "lapsed_regulars",
                "action_type": "send_offer",
                "template_id": template.id,
                "user_ids": [lapsed.id],
            },
        )
        assert r.status_code == 200, r.text
        result = r.json()["data"]
        assert result["rewards_issued"] == 1
        assert result["already_had"] == 0

        statuses = (
            await db_session.execute(
                select(Reward.code, Reward.status).where(Reward.user_id == lapsed.id)
            )
        ).all()
        by_code = dict(statuses)
        assert by_code["HS-STALE01"] == "expired"
        assert [s for c, s in statuses if c != "HS-STALE01"] == ["issued"]


class TestSendReminder:
    async def test_texts_only_consented_holders_and_creates_nothing(
        self, client, db_session, owner, settings_row, template, monkeypatch
    ):
        sent: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "app.services.sms_service.send_sms", lambda phone, body: sent.append((phone, body))
        )

        now = datetime.now(timezone.utc)
        consented = await _customer_with_orders(db_session, "+14165550005", "Amy", [10])
        silent = await _customer_with_orders(db_session, "+14165550006", "Ben", [12])
        db_session.add(UserNotificationPreference(user_id=consented.id, sms_marketing_opt_in=True))
        r1 = Reward(
            user_id=consented.id, reward_template_id=template.id, code="HS-REMIND1",
            status="issued", expires_at=now + timedelta(days=2),
        )
        r2 = Reward(
            user_id=silent.id, reward_template_id=template.id, code="HS-REMIND2",
            status="issued", expires_at=now + timedelta(days=2),
        )
        db_session.add_all([r1, r2])
        await db_session.commit()

        rewards_before = len((await db_session.execute(select(Reward))).scalars().all())

        _admin(client, owner)
        r = await client.post(
            ACT,
            json={
                "insight_key": "expiring_rewards",
                "action_type": "send_reminder",
                "reward_ids": [r1.id, r2.id],
            },
        )
        assert r.status_code == 200, r.text
        result = r.json()["data"]
        assert result["targeted"] == 2
        assert result["rewards_issued"] == 0
        assert result["sms_sent"] == 1
        assert result["sms_skipped"] == 1

        rewards_after = len((await db_session.execute(select(Reward))).scalars().all())
        assert rewards_after == rewards_before  # a reminder never mints rewards

        assert len(sent) == 1
        assert "HS-REMIND1" in sent[0][1]
        assert "expires soon" in sent[0][1]

    async def test_stale_page_cannot_text_about_non_expiring_rewards(
        self, client, db_session, owner, settings_row, template, monkeypatch
    ):
        """The server re-validates the expiry window; client-supplied ids for
        rewards that already died or have weeks left must never trigger an
        'expires soon' text."""
        sent: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "app.services.sms_service.send_sms", lambda phone, body: sent.append((phone, body))
        )
        now = datetime.now(timezone.utc)
        u = await _customer_with_orders(db_session, "+14165550008", "Cara", [5])
        db_session.add(UserNotificationPreference(user_id=u.id, sms_marketing_opt_in=True))
        dead = Reward(
            user_id=u.id, reward_template_id=template.id, code="HS-DEAD001",
            status="issued", expires_at=now - timedelta(days=1),
        )
        far = Reward(
            user_id=u.id, reward_template_id=template.id, code="HS-FAR0001",
            status="redeemed", redeemed_at=now, expires_at=now + timedelta(days=30),
        )
        db_session.add_all([dead, far])
        await db_session.commit()

        _admin(client, owner)
        r = await client.post(
            ACT,
            json={
                "insight_key": "expiring_rewards",
                "action_type": "send_reminder",
                "reward_ids": [dead.id, far.id],
            },
        )
        assert r.status_code == 400
        assert sent == []


class TestOutcomes:
    async def test_revenue_attributes_back_to_the_decision(
        self, client, db_session, owner, settings_row, template
    ):
        raymond = await _customer_with_orders(
            db_session, "+14165550001", "Raymond Wu", [49, 42, 35, 28]
        )
        _admin(client, owner)
        r = await client.post(
            ACT,
            json={
                "insight_key": "lapsed_regulars",
                "action_type": "send_offer",
                "template_id": template.id,
                "user_ids": [raymond.id],
            },
        )
        assert r.status_code == 200, r.text

        # Raymond comes back: redeems the offer on a $56.78 order.
        now = datetime.now(timezone.utc)
        reward = (
            await db_session.execute(select(Reward).where(Reward.user_id == raymond.id))
        ).scalar_one()
        reward.status = "redeemed"
        reward.redeemed_at = now + timedelta(hours=1)
        db_session.add(
            Order(
                user_id=raymond.id,
                subtotal_cents=5_678,
                discount_cents=0,
                tax_cents=0,
                total_cents=5_678,
                reward_id=reward.id,
                item_count=2,
                status="completed",
                created_at=now + timedelta(hours=1),
            )
        )
        await db_session.commit()

        # A later cancelled order referencing the same reward must not inflate
        # the number the owner reads out loud.
        db_session.add(
            Order(
                user_id=raymond.id,
                subtotal_cents=99_999,
                discount_cents=0,
                tax_cents=0,
                total_cents=99_999,
                reward_id=reward.id,
                item_count=1,
                status="cancelled",
                created_at=now + timedelta(hours=2),
            )
        )
        await db_session.commit()

        data = (await client.get(INSIGHTS)).json()["data"]
        assert len(data["actions"]) == 1
        outcome = data["actions"][0]["outcome"]
        assert outcome["redeemed"] == 1
        assert outcome["revenue_cents"] == 5_678
        assert data["actions"][0]["template_name"] == "10% off"

    async def test_reminder_outcomes_respect_the_window_and_never_double_count(
        self, client, db_session, owner, settings_row, template
    ):
        """Only redemptions AFTER the reminder count, and rewards minted by an
        offer action (source_code dec-*) credit that offer — not the reminder
        that later nudged them — so the ledger's total matches real revenue."""
        from app.models import InsightAction

        now = datetime.now(timezone.utc)
        u = await _customer_with_orders(db_session, "+14165550009", "Dee", [30])

        # All three are constructed already-redeemed (the partial unique index
        # forbids two ISSUED rewards per user+template anyway); the outcome
        # query only compares redeemed_at against the action timestamp.
        def _redeemed(code, redeemed_at, source_code=None):
            return Reward(
                user_id=u.id, reward_template_id=template.id, code=code,
                status="redeemed", source_code=source_code,
                expires_at=now + timedelta(days=3), redeemed_at=redeemed_at,
            )

        # Redeemed BEFORE the reminder existed — must not count.
        pre = _redeemed("HS-PRE0001", now - timedelta(days=2))
        # Redeemed after — counts.
        post = _redeemed("HS-POST001", now)
        # Minted by an earlier offer action — excluded from the reminder's tally.
        offer_minted = _redeemed("HS-OFFER01", now, source_code="dec-aabbccdd")
        db_session.add_all([pre, post, offer_minted])
        await db_session.flush()

        db_session.add(
            InsightAction(
                insight_key="expiring_rewards",
                action_type="send_reminder",
                source_code="dec-11223344",
                acted_by=owner.id,
                targeted_count=3,
                sms_sent=1,
                sms_skipped=2,
                params={"reward_ids": [pre.id, post.id, offer_minted.id]},
                created_at=now - timedelta(days=1),
            )
        )
        for rw, cents in ((post, 4_000), (offer_minted, 7_000)):
            db_session.add(
                Order(
                    user_id=u.id, subtotal_cents=cents, discount_cents=0,
                    tax_cents=0, total_cents=cents, reward_id=rw.id,
                    item_count=1, status="completed", created_at=now,
                )
            )
        await db_session.commit()

        _admin(client, owner)
        data = (await client.get(INSIGHTS)).json()["data"]
        reminder = next(a for a in data["actions"] if a["action_type"] == "send_reminder")
        # Only the plain post-action redemption counts: not the pre-action one,
        # not the offer-minted one.
        assert reminder["outcome"]["redeemed"] == 1
        assert reminder["outcome"]["revenue_cents"] == 4_000
