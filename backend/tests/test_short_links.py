"""Integration tests for short links."""

from datetime import datetime, timedelta, timezone

from app.models import ShortLink


class TestShortLinks:
    async def test_create_short_link(self, db_session):
        link = ShortLink(
            code="a7k9p2",
            destination_url="https://hongshing.ca/r/HS-A7K9P2",
            link_type="reward",
        )
        db_session.add(link)
        await db_session.flush()
        assert link.id is not None
        assert link.code == "a7k9p2"
        assert link.click_count == 0

    async def test_click_count_increment(self, db_session):
        link = ShortLink(
            code="clickme",
            destination_url="https://hongshing.ca/r/test",
            link_type="redirect",
        )
        db_session.add(link)
        await db_session.flush()

        link.click_count += 1
        await db_session.flush()
        assert link.click_count == 1

    async def test_expired_link(self, db_session):
        link = ShortLink(
            code="expired1",
            destination_url="https://hongshing.ca/expired",
            link_type="reward",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db_session.add(link)
        await db_session.flush()

        assert link.expires_at < datetime.now(timezone.utc)

    async def test_unsubscribe_link_type(self, db_session):
        link = ShortLink(
            code="u8kx2",
            destination_url="https://hongshing.ca/unsubscribe",
            link_type="unsubscribe",
        )
        db_session.add(link)
        await db_session.flush()
        assert link.link_type == "unsubscribe"
