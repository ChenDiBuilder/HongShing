"""End-to-end QR campaign funnel — the agent-testable acquisition scenario.

Exercises the whole funnel in-process against the test DB and asserts that a
scanned QR's ``source_code`` stays attached to the customer through signup and
their session, and then surfaces in the admin analytics as per-campaign
scans / signups / rewards / orders / revenue + conversion.

Funnel under test:
    admin creates campaign
      -> anonymous QR scan beacon           (POST /api/tracking/qr-scan-confirmed)
      -> send + verify OTP carrying source  (SignupEvent written, session cookie set)
      -> returning customer via cookie       (GET /api/customer/me)
      -> claim reward                        (Reward attributed to the campaign)
      -> place an order                      (Order attributed via user -> SignupEvent)
      -> admin analytics reflects all of it  (GET /api/admin/analytics)

Runs fully in-process (no server, no real SMS): the ASGI test client doesn't run
the app lifespan, and the OTP is made deterministic by pinning secrets.randbelow
for the 6-digit draw so the test can "read" the texted code.
"""

import secrets

from sqlalchemy import select

from app.models import Reward, RewardTemplate, SignupEvent
from app.services.auth_service import create_access_token

SOURCE = "receipt"
PHONE = "+16475550199"
ITEM_PRICE_CENTS = 1500


class TestCampaignFunnel:
    async def test_full_qr_campaign_funnel(self, client, owner_user, db_session, monkeypatch):
        # Make the OTP deterministic so the test can "read" it. Guard on n so only
        # the send-otp draw (randbelow(1_000_000)) is pinned; other secrets usage
        # (e.g. reward-code generation) keeps its real randomness.
        real_randbelow = secrets.randbelow
        monkeypatch.setattr(
            secrets, "randbelow", lambda n: 123456 if n == 1_000_000 else real_randbelow(n)
        )
        code = "123456"

        # --- admin authenticates (owner) ---
        admin_token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", admin_token)

        # A reward the campaign hands out on claim.
        template = RewardTemplate(
            name="10% off next order",
            code_prefix="HS",
            reward_type="percent",
            reward_value=10,
            valid_days=30,
        )
        db_session.add(template)
        await db_session.flush()

        # --- 1) admin generates the QR campaign ---
        resp = await client.post(
            "/api/admin/qr-campaigns",
            json={
                "name": "Receipt QR",
                "source_code": SOURCE,
                "landing_headline": "Thanks for dining with us",
                "reward_template_id": template.id,
            },
        )
        assert resp.status_code == 200, resp.text
        campaign = resp.json()["data"]
        campaign_id = campaign["id"]
        assert campaign["source_code"] == SOURCE

        # --- 2) anonymous scan beacon (customer scans the QR, page renders) ---
        resp = await client.post(
            "/api/tracking/qr-scan-confirmed",
            params={"source_code": SOURCE, "campaign_id": campaign_id, "session_id": "sess-agent-1"},
        )
        assert resp.status_code == 200, resp.text

        # --- 3) signup: send + verify OTP, carrying the scanned source ---
        resp = await client.post(
            "/api/auth/send-otp", json={"phone": PHONE, "source_code": SOURCE}
        )
        assert resp.status_code == 202, resp.text

        resp = await client.post(
            "/api/auth/verify-otp",
            json={
                "phone": PHONE,
                "code": code,
                "source_code": SOURCE,
                "campaign_id": campaign_id,
                "marketing_opt_in": True,
            },
        )
        assert resp.status_code == 200, resp.text
        # Session cookie issued by verify-otp (kept in the client cookie jar).
        assert "access_token" in client.cookies

        # The scan "stays with" the customer: attribution is bound at signup.
        signup = (
            await db_session.execute(select(SignupEvent).where(SignupEvent.phone == PHONE))
        ).scalar_one()
        assert signup.source_code == SOURCE
        assert signup.qr_campaign_id == campaign_id

        # --- 4) returning customer recognized purely by the session cookie ---
        resp = await client.get("/api/customer/me")
        assert resp.status_code == 200, resp.text
        assert resp.json()["phone"] == PHONE

        # --- 5) claim the campaign reward (attributed to the campaign) ---
        resp = await client.post(
            "/api/rewards/claim", json={"source_code": SOURCE, "campaign_id": campaign_id}
        )
        assert resp.status_code == 200, resp.text
        reward = (
            await db_session.execute(select(Reward).where(Reward.source_code == SOURCE))
        ).scalar_one()
        assert reward.qr_campaign_id == campaign_id

        # --- 6) place an order (attributed to the campaign via user -> SignupEvent) ---
        resp = await client.post(
            "/api/cart/items",
            json={
                "menu_item_id": "11111111-1111-1111-1111-111111111111",
                "name": "General Tso Chicken",
                "price_cents": ITEM_PRICE_CENTS,
                "quantity": 1,
            },
        )
        assert resp.status_code == 200, resp.text
        resp = await client.post("/api/cart/checkout", json={})
        assert resp.status_code == 200, resp.text

        # --- 7) admin analytics reflects the full attributed funnel ---
        resp = await client.get("/api/admin/analytics?days=14")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        by_source = {s["source_code"]: s for s in data["sources"]}
        assert SOURCE in by_source, f"campaign source missing from analytics: {by_source.keys()}"
        row = by_source[SOURCE]
        assert row["campaign_name"] == "Receipt QR"
        assert row["scans"] >= 1
        assert row["signups"] >= 1
        assert row["rewards_issued"] >= 1
        # The gap we closed: orders + revenue attributed per campaign.
        assert row["orders"] == 1, row
        assert row["revenue_cents"] == ITEM_PRICE_CENTS, row
        # Conversion rates are populated (not None) once the funnel has data.
        assert row["scan_to_signup_rate"] is not None
        assert row["signup_to_order_rate"] == 100.0, row

        # Overall funnel conversion is exposed too.
        assert data["funnel"]["orders"] >= 1
        assert data["funnel"]["signup_to_order_rate"] is not None
