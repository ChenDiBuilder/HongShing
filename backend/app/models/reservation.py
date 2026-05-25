import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class ReservationSlot(Base):
    __tablename__ = "reservation_slots"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    max_party_size: Mapped[int] = mapped_column(Integer, default=6)
    max_reservations: Mapped[int] = mapped_column(Integer, default=4)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    guest_name: Mapped[str] = mapped_column(String(100), nullable=False)
    guest_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
