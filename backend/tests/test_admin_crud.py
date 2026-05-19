"""Integration tests for admin CRUD routes."""

from app.models import QRCampaign, RewardTemplate, RestaurantSettings
from app.services.auth_service import create_access_token


# --- QR Campaigns ---
class TestAdminQR:
    async def test_list_campaigns(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/qr-campaigns")
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_create_campaign(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.post(
            "/api/admin/qr-campaigns?name=Test&source_code=receipt&landing_headline=Scan+to+save"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "Test"

    async def test_update_campaign(self, client, owner_user, db_session):
        campaign = QRCampaign(name="Old", source_code="old_src", active=True)
        db_session.add(campaign)
        await db_session.flush()

        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.patch(
            f"/api/admin/qr-campaigns/{campaign.id}?name=Updated"
        )
        assert resp.status_code == 200


# --- Reward Templates ---
class TestAdminRewards:
    async def test_create_template(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.post(
            "/api/admin/reward-templates?name=$5+Off&reward_type=fixed&reward_value=500"
        )
        assert resp.status_code == 200

    async def test_list_templates(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/reward-templates")
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_redeem_reward(self, client, owner_user, db_session, customer_user):
        from app.models import Reward

        template = RewardTemplate(name="Test", code_prefix="HS", reward_type="fixed", reward_value=500)
        db_session.add(template)
        await db_session.flush()  # flush to get template.id

        reward = Reward(
            user_id=customer_user.id,
            reward_template_id=template.id,
            code="HS-REDEEM",
            status="issued",
        )
        db_session.add(reward)
        await db_session.flush()

        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.patch(f"/api/admin/rewards/{reward.id}/redeem")
        assert resp.status_code == 200


# --- Customers ---
class TestAdminCustomers:
    async def test_list_customers(self, client, owner_user, customer_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/customers")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1

    async def test_search_customers(self, client, owner_user, customer_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/customers?search=555")  # partial phone match
        assert resp.status_code == 200

    async def test_get_customer_detail(self, client, owner_user, customer_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get(f"/api/admin/customers/{customer_user.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["phone"] == "+16475551234"
        assert "rewards" in data
        assert "consent" in data


# --- Settings ---
class TestAdminSettings:
    async def test_get_settings(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/settings")
        assert resp.status_code == 200

    async def test_update_settings(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.patch(
            "/api/admin/settings?restaurant_name=Test+Restaurant&primary_color=%2300FF00"
        )
        assert resp.status_code == 200


# --- Notifications ---
class TestAdminNotifications:
    async def test_send_sms_requires_manager(self, client, staff_user):
        token = create_access_token(staff_user.id, "staff")
        client.cookies.set("admin_access_token", token)
        resp = await client.post(
            "/api/admin/notifications/sms?body=Hello&message_type=marketing"
        )
        assert resp.status_code == 403

    async def test_send_sms_as_owner(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.post(
            "/api/admin/notifications/sms?body=Hello&message_type=transactional"
        )
        assert resp.status_code == 200

    async def test_list_notifications(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/notifications")
        assert resp.status_code == 200
