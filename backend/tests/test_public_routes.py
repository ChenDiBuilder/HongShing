"""Integration tests for public routes."""


class TestLandingConfig:
    async def test_returns_defaults_when_no_settings(self, client, db_session):
        from sqlalchemy import delete
        from app.models import RestaurantSettings

        # Ensure no settings exist
        await db_session.execute(delete(RestaurantSettings))
        await db_session.flush()

        resp = await client.get("/api/public/landing-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["restaurant_name"] == "HongShing"
        assert data["primary_color"] == "#C41E3A"
        assert data["allow_order_without_signup"] is True

    async def test_returns_settings_when_present(self, client, db_session):
        from app.models import RestaurantSettings

        settings = RestaurantSettings(
            id="00000000-0000-0000-0000-000000000001",
            restaurant_name="Test Restaurant",
            primary_color="#0000FF",
            allow_order_without_signup=False,
        )
        db_session.add(settings)
        await db_session.flush()

        resp = await client.get("/api/public/landing-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["restaurant_name"] == "Test Restaurant"
        assert data["primary_color"] == "#0000FF"
        assert data["allow_order_without_signup"] is False

    async def test_source_filters_campaign(self, client, db_session):
        from app.models import QRCampaign, RestaurantSettings

        # Need settings row for the route to check campaigns
        settings = RestaurantSettings(id="00000000-0000-0000-0000-000000000001")
        db_session.add(settings)
        await db_session.flush()

        campaign = QRCampaign(
            name="Test Campaign",
            source_code="receipt",
            landing_headline="Scan to save!",
            active=True,
        )
        db_session.add(campaign)
        await db_session.flush()

        resp = await client.get("/api/public/landing-config?source=receipt")
        assert resp.status_code == 200
        data = resp.json()
        assert data["campaign"] is not None
        assert data["campaign"]["source_code"] == "receipt"
        assert data["campaign"]["landing_headline"] == "Scan to save!"

    async def test_unknown_source_returns_no_campaign(self, client):
        resp = await client.get("/api/public/landing-config?source=unknown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["campaign"] is None
