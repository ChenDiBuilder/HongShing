"""Integration tests for customer routes."""

from app.models import QRCampaign, RewardTemplate, RestaurantSettings
from app.services.auth_service import create_access_token


class TestCustomerProfile:
    async def test_get_profile_requires_auth(self, client):
        resp = await client.get("/api/customer/me")
        assert resp.status_code == 401

    async def test_get_profile_as_customer(self, client, customer_user):
        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("access_token", token)
        resp = await client.get("/api/customer/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone"] == "+16475551234"

    async def test_update_profile(self, client, customer_user, db_session):
        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("access_token", token)
        resp = await client.patch("/api/customer/me?name=Updated&email=test@example.com")
        assert resp.status_code == 200


class TestRewardClaim:
    async def test_claim_reward_with_default_template(self, client, customer_user, db_session):
        # Create settings with default template
        settings = RestaurantSettings(id="00000000-0000-0000-0000-000000000001")
        db_session.add(settings)
        template = RewardTemplate(name="Welcome $5", code_prefix="HS", reward_type="fixed", reward_value=500, valid_days=30)
        db_session.add(template)
        await db_session.flush()
        settings.default_reward_template_id = template.id
        await db_session.flush()

        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("access_token", token)

        resp = await client.post("/api/rewards/claim", json={"source_code": "receipt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["reward"]["code"].startswith("HS-")
        assert data["reward"]["status"] == "issued"
        assert data["short_link"] is not None

    async def test_claim_duplicate_returns_existing(self, client, customer_user, db_session):
        settings = RestaurantSettings(id="00000000-0000-0000-0000-000000000001")
        db_session.add(settings)
        template = RewardTemplate(name="Test", code_prefix="HS", reward_type="fixed", reward_value=500, valid_days=30)
        db_session.add(template)
        await db_session.flush()
        settings.default_reward_template_id = template.id
        await db_session.flush()

        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("access_token", token)

        # First claim
        resp1 = await client.post("/api/rewards/claim", json={})
        assert resp1.status_code == 200
        code1 = resp1.json()["reward"]["code"]

        # Second claim — returns same reward
        resp2 = await client.post("/api/rewards/claim", json={})
        assert resp2.status_code == 200
        assert resp2.json()["reward"]["code"] == code1

    async def test_claim_no_template_returns_400(self, client, customer_user):
        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("access_token", token)
        resp = await client.post("/api/rewards/claim", json={})
        assert resp.status_code == 400


class TestOrderRedirect:
    async def test_redirect_returns_url(self, client, db_session):
        settings = RestaurantSettings(
            id="00000000-0000-0000-0000-000000000001",
            external_ordering_url="https://order.example.com",
        )
        db_session.add(settings)
        await db_session.flush()

        resp = await client.post("/api/redirects/order", json={"source_code": "receipt"})
        assert resp.status_code == 200
        assert resp.json()["destination_url"] == "https://order.example.com"

    async def test_redirect_no_url_returns_fallback(self, client):
        resp = await client.post("/api/redirects/order", json={})
        assert resp.status_code == 200
        assert resp.json()["destination_url"] == "https://hongshing.ca/order"
