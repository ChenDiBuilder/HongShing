"""Integration tests for QR tracking and consent routes."""

from sqlalchemy import select

from app.models import QRScanEvent, ShortLink, UserNotificationPreference
from app.services.auth_service import create_access_token


class TestQRTracking:
    async def test_scan_confirmed_beacon(self, client):
        resp = await client.post(
            "/api/tracking/qr-scan-confirmed?source_code=receipt&session_id=sess-1"
        )
        assert resp.status_code == 200


class TestConsent:
    async def test_update_consent_opt_in(self, client, customer_user, db_session):
        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("access_token", token)

        resp = await client.post(
            "/api/consent/preferences?sms_marketing_opt_in=true"
        )
        assert resp.status_code == 200

        # Verify in DB
        result = await db_session.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == customer_user.id
            )
        )
        prefs = result.scalar_one()
        assert prefs.sms_marketing_opt_in is True
        assert prefs.consent_source == "api"

    async def test_update_consent_opt_out(self, client, customer_user, db_session):
        # Create preferences first
        prefs = UserNotificationPreference(
            user_id=customer_user.id,
            sms_marketing_opt_in=True,
            consent_source="registration",
        )
        db_session.add(prefs)
        await db_session.flush()

        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("access_token", token)

        resp = await client.post(
            "/api/consent/preferences?sms_marketing_opt_in=false"
        )
        assert resp.status_code == 200

        # Verify opt-out
        result = await db_session.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == customer_user.id
            )
        )
        updated = result.scalar_one()
        assert updated.sms_marketing_opt_in is False
        assert updated.unsubscribed_at is not None

    async def test_unsubscribe_via_link(self, client, customer_user, db_session):
        # Create preferences
        prefs = UserNotificationPreference(
            user_id=customer_user.id,
            sms_marketing_opt_in=True,
        )
        db_session.add(prefs)
        # Create unsubscribe short link
        link = ShortLink(
            code="unsub-1",
            destination_url="/unsubscribe",
            link_type="unsubscribe",
            user_id=customer_user.id,
        )
        db_session.add(link)
        await db_session.flush()

        resp = await client.get("/api/consent/unsubscribe/unsub-1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify opt-out
        result = await db_session.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == customer_user.id
            )
        )
        updated = result.scalar_one()
        assert updated.sms_marketing_opt_in is False

    async def test_unsubscribe_invalid_token(self, client):
        resp = await client.get("/api/consent/unsubscribe/invalid-token")
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
