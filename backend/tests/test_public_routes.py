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
        assert data["restaurant_name"] == "Restaurant"  # brand-neutral default (SCRUM-49)
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

    async def test_surfaces_display_fields(self, client, db_session):
        """PRD-12 S8 — address/phone/hours/pickup/tax/currency reach the SPA, and
        hours_json is parsed into a dict (or stays None on bad JSON)."""
        import json

        from app.models import RestaurantSettings

        settings = RestaurantSettings(
            id="00000000-0000-0000-0000-000000000001",
            restaurant_name="Test Restaurant",
            primary_color="#0000FF",
            address="1 Test St",
            contact_phone="+14165550123",
            hours_json=json.dumps({"Mon": "9–5", "Tue": "Closed"}),
            pickup_estimate="15 min",
            tax_rate=0.05,
            currency_symbol="$",
        )
        db_session.add(settings)
        await db_session.flush()

        data = (await client.get("/api/public/landing-config")).json()
        assert data["address"] == "1 Test St"
        assert data["contact_phone"] == "+14165550123"
        assert data["hours_display"] == {"Mon": "9–5", "Tue": "Closed"}
        assert data["pickup_estimate"] == "15 min"
        assert data["tax_rate"] == 0.05
        assert data["currency_symbol"] == "$"

    async def test_surfaces_copy_legal_locale_storefront(self, client, db_session):
        """PRD-12 S3/S6/S9 — tagline/reward_success_copy/legal_name/languages/
        storefront_enabled reach the SPA; otp_sms_template and
        business_mailing_address are intentionally NOT exposed."""
        from app.models import RestaurantSettings

        settings = RestaurantSettings(
            id="00000000-0000-0000-0000-000000000001",
            restaurant_name="Test Restaurant",
            primary_color="#0000FF",
            tagline="Order ahead, earn perks.",
            reward_success_copy="Reward unlocked!",
            otp_sms_template="Code {code} for {restaurant}.",
            legal_name="Test Restaurant Inc.",
            business_mailing_address="1 Test St, Toronto",
            languages="en,zh",
            storefront_enabled=True,
        )
        db_session.add(settings)
        await db_session.flush()

        data = (await client.get("/api/public/landing-config")).json()
        assert data["tagline"] == "Order ahead, earn perks."
        assert data["reward_success_copy"] == "Reward unlocked!"
        assert data["legal_name"] == "Test Restaurant Inc."
        assert data["languages"] == ["en", "zh"]
        assert data["storefront_enabled"] is True
        # Server-side-only fields must never leak to the public SPA.
        assert "otp_sms_template" not in data
        assert "business_mailing_address" not in data

    async def test_bad_hours_json_does_not_500(self, client, db_session):
        from app.models import RestaurantSettings

        settings = RestaurantSettings(
            id="00000000-0000-0000-0000-000000000001",
            restaurant_name="Test Restaurant",
            primary_color="#0000FF",
            hours_json="not valid json{",
        )
        db_session.add(settings)
        await db_session.flush()

        resp = await client.get("/api/public/landing-config")
        assert resp.status_code == 200
        assert resp.json()["hours_display"] is None

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
