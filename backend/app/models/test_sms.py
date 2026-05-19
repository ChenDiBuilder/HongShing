"""Test-mode SMS messages table and endpoint — only active when APP_ENV=testing."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TestSmsMessage(Base):
    __tablename__ = "test_sms_messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: __import__("uuid").uuid4().hex,  # noqa: B023
    )
    phone: Mapped[str] = mapped_column(String(20))
    otp_code: Mapped[str] = mapped_column(String(6))  # Plaintext — test mode only
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
