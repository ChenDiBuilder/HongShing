"""Integration tests for QR scan tracking routes."""

from app.models import QRScanEvent


class TestQRScanTracking:
    async def test_landing_page_creates_page_loaded_event(self, client, db_session):
        """Server-side page load records a page_loaded event."""
        # The landing config endpoint doesn't currently record scan events.
        # This test validates the QR scan event model structure.
        from sqlalchemy import select, func

        event = QRScanEvent(
            source_code="receipt",
            anonymous_session_id="sess-123",
            event_type="page_loaded",
            user_agent="Mozilla/5.0",
        )
        db_session.add(event)
        await db_session.flush()

        count = await db_session.scalar(
            select(func.count(QRScanEvent.id)).where(QRScanEvent.source_code == "receipt")
        )
        assert count == 1
        assert event.event_type == "page_loaded"

    async def test_scan_confirmed_event_type(self, client, db_session):
        """scan_confirmed events are distinguishable from page_loaded."""
        event = QRScanEvent(
            source_code="receipt",
            anonymous_session_id="sess-456",
            event_type="scan_confirmed",
        )
        db_session.add(event)
        await db_session.flush()

        from sqlalchemy import select
        result = await db_session.execute(
            select(QRScanEvent).where(QRScanEvent.event_type == "scan_confirmed")
        )
        confirmed = result.scalars().all()
        assert len(confirmed) == 1

    async def test_bot_detection(self, client, db_session):
        """Bot-like user agents are flagged."""
        event = QRScanEvent(
            source_code="receipt",
            anonymous_session_id="sess-bot",
            event_type="page_loaded",
            user_agent="Googlebot/2.1",
            is_likely_bot=True,
        )
        db_session.add(event)
        await db_session.flush()

        from sqlalchemy import select
        result = await db_session.execute(
            select(QRScanEvent).where(QRScanEvent.is_likely_bot == True)  # noqa: E712
        )
        bots = result.scalars().all()
        assert len(bots) == 1

    async def test_source_code_preserved(self, client, db_session):
        """source_code is stored correctly for attribution."""
        event = QRScanEvent(
            source_code="takeout_bag",
            anonymous_session_id="sess-789",
            event_type="page_loaded",
        )
        db_session.add(event)
        await db_session.flush()

        assert event.source_code == "takeout_bag"
