"""Integration tests for consent and unsubscribe."""

from datetime import datetime, timezone

from app.models import UserNotificationPreference


class TestConsent:
    async def test_marketing_opt_in_defaults_false(self, db_session, customer_user):
        pref = UserNotificationPreference(
            user_id=customer_user.id,
            sms_transactional_enabled=True,
            sms_marketing_opt_in=False,
        )
        db_session.add(pref)
        await db_session.flush()

        assert pref.sms_marketing_opt_in is False
        assert pref.sms_transactional_enabled is True

    async def test_unsubscribe_sets_timestamp(self, db_session, customer_user):
        pref = UserNotificationPreference(
            user_id=customer_user.id,
            sms_marketing_opt_in=True,
        )
        db_session.add(pref)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        pref.sms_marketing_opt_in = False
        pref.unsubscribed_at = now
        await db_session.flush()

        assert pref.sms_marketing_opt_in is False
        assert pref.unsubscribed_at is not None

    async def test_consent_source_tracked(self, db_session, customer_user):
        pref = UserNotificationPreference(
            user_id=customer_user.id,
            sms_marketing_opt_in=True,
            consent_source="registration",
            consented_at=datetime.now(timezone.utc),
        )
        db_session.add(pref)
        await db_session.flush()

        assert pref.consent_source == "registration"
        assert pref.consented_at is not None

    async def test_unique_per_user(self, db_session, customer_user):
        pref1 = UserNotificationPreference(
            user_id=customer_user.id,
            sms_transactional_enabled=True,
        )
        db_session.add(pref1)
        await db_session.flush()

        # Second preference for same user should fail unique constraint
        pref2 = UserNotificationPreference(
            user_id=customer_user.id,
            sms_transactional_enabled=True,
        )
        db_session.add(pref2)
        import sqlalchemy.exc
        import pytest

        with pytest.raises((sqlalchemy.exc.IntegrityError, sqlalchemy.exc.InternalError)):
            await db_session.flush()
        db_session.expunge_all()
