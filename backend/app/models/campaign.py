import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RestaurantSettings(Base):
    __tablename__ = "restaurant_settings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: "00000000-0000-0000-0000-000000000001",
    )
    restaurant_name: Mapped[str] = mapped_column(String(200), default="Restaurant")
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), default="#C41E3A")
    secondary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    external_ordering_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_ordering_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    allow_order_without_signup: Mapped[bool] = mapped_column(Boolean, default=True)
    default_reward_template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    timezone: Mapped[str] = mapped_column(String(50), default="America/Toronto")
    privacy_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    support_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class QRCampaign(Base):
    __tablename__ = "qr_campaigns"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    source_code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reward_template_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    landing_headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    landing_subtitle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class QRScanEvent(Base):
    __tablename__ = "qr_scan_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    qr_campaign_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    source_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    anonymous_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    event_type: Mapped[str] = mapped_column(String(20), default="page_loaded")
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_likely_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SignupEvent(Base):
    __tablename__ = "signup_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    phone: Mapped[str] = mapped_column(String(20))
    source_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    qr_campaign_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    signup_method: Mapped[str] = mapped_column(String(30), default="qr")
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
