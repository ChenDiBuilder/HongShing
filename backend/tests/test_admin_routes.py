"""Integration tests for admin routes."""

from sqlalchemy import select

from app.models import QRCampaign, User
from app.services.auth_service import create_access_token, hash_password


class TestDashboard:
    async def test_dashboard_returns_counts(self, client, db_session):
        """Dashboard returns zero counts for empty database."""
        # Create owner directly in test
        owner = User(
            email="test-owner@example.com",
            name="Owner",
            password_hash=hash_password("admin123"),
            role="owner",
        )
        db_session.add(owner)
        await db_session.flush()

        token = create_access_token(owner.id, "owner")
        # httpx uses domain from base_url; set cookie for that domain
        client.cookies.set("admin_access_token", token)

        resp = await client.get("/api/admin/dashboard")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "data" in data
        assert data["data"]["total_customers"] == 0
        assert data["data"]["active_campaigns"] == 0

    async def test_dashboard_with_data(self, client, db_session):
        """Dashboard returns correct counts with seeded data."""
        # Owner
        owner = User(
            email="test-owner2@example.com",
            name="Owner",
            password_hash=hash_password("admin123"),
            role="owner",
        )
        db_session.add(owner)
        # Customer
        customer = User(phone="+16475559999", role="customer")
        db_session.add(customer)
        # Campaign
        campaign = QRCampaign(name="Test", source_code="receipt", active=True)
        db_session.add(campaign)
        await db_session.flush()

        token = create_access_token(owner.id, "owner")
        client.cookies.set("admin_access_token", token)

        resp = await client.get("/api/admin/dashboard")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["total_customers"] == 1
        assert data["active_campaigns"] == 1

    async def test_dashboard_blocked_without_auth(self, client):
        resp = await client.get("/api/admin/dashboard")
        assert resp.status_code == 401
