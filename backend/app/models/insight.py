import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InsightAction(Base):
    """A decision the owner acted on — the audit trail of the decisioning loop.

    Each action gets its own unique source_code, stamped onto every reward it
    issues. Outcomes (redemptions, orders, revenue) are then derived live by
    joining rewards/orders on that code — no separate outcome bookkeeping to
    drift out of sync.
    """

    __tablename__ = "insight_actions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    insight_key: Mapped[str] = mapped_column(String(50))
    action_type: Mapped[str] = mapped_column(String(30))
    source_code: Mapped[str] = mapped_column(String(50), unique=True)
    reward_template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("reward_templates.id"), nullable=True
    )
    acted_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    targeted_count: Mapped[int] = mapped_column(Integer, default=0)
    rewards_issued: Mapped[int] = mapped_column(Integer, default=0)
    already_had: Mapped[int] = mapped_column(Integer, default=0)
    sms_sent: Mapped[int] = mapped_column(Integer, default=0)
    sms_skipped: Mapped[int] = mapped_column(Integer, default=0)
    # send_offer: {"user_ids": [...]}; send_reminder: {"reward_ids": [...]}
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
