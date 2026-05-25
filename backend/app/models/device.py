import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unpaired")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
