import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    cart_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    menu_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
