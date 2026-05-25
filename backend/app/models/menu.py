import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    category_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    popular: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
