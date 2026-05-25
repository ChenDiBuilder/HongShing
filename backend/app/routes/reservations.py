from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_customer
from app.models import Reservation, ReservationSlot, User

router = APIRouter(prefix="/api", tags=["reservations"])

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@router.get("/reservations/slots")
async def available_slots(
    reservation_date: date = Query(...),
    party_size: int = Query(default=2),
    db: AsyncSession = Depends(get_db),
):
    day_of_week = reservation_date.weekday()
    result = await db.execute(
        select(ReservationSlot)
        .where(
            ReservationSlot.day_of_week == day_of_week,
            ReservationSlot.is_active == True,
            ReservationSlot.max_party_size >= party_size,
        )
        .order_by(ReservationSlot.start_time)
    )
    slots = result.scalars().all()

    available = []
    for slot in slots:
        count_result = await db.execute(
            select(func.count(Reservation.id))
            .where(
                Reservation.reservation_date == reservation_date,
                Reservation.start_time == slot.start_time,
                Reservation.status != "cancelled",
            )
        )
        count = count_result.scalar() or 0
        available.append(
            {
                "id": slot.id,
                "start_time": slot.start_time.isoformat() if slot.start_time else None,
                "end_time": slot.end_time.isoformat() if slot.end_time else None,
                "max_party_size": slot.max_party_size,
                "available_spots": max(0, slot.max_reservations - count),
                "max_reservations": slot.max_reservations,
            }
        )
    return {"slots": available}


class CreateReservationRequest(BaseModel):
    reservation_date: str
    start_time: str
    party_size: int
    notes: Optional[str] = None


@router.post("/reservations")
async def create_reservation(
    body: CreateReservationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    date_parts = body.reservation_date.split("-")
    time_parts = body.start_time.split(":")
    reservation_date = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
    start = time(int(time_parts[0]), int(time_parts[1]))

    day_of_week = reservation_date.weekday()
    slot_result = await db.execute(
        select(ReservationSlot)
        .where(
            ReservationSlot.day_of_week == day_of_week,
            ReservationSlot.start_time == start,
            ReservationSlot.is_active == True,
        )
    )
    slot = slot_result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=400, detail="Time slot not available")

    if body.party_size > slot.max_party_size:
        raise HTTPException(status_code=400, detail=f"Maximum party size is {slot.max_party_size}")

    count_result = await db.execute(
        select(func.count(Reservation.id))
        .where(
            Reservation.reservation_date == reservation_date,
            Reservation.start_time == start,
            Reservation.status != "cancelled",
        )
    )
    count = count_result.scalar() or 0
    if count >= slot.max_reservations:
        raise HTTPException(status_code=400, detail="Slot is fully booked")

    reservation = Reservation(
        user_id=current_user.id,
        reservation_date=reservation_date,
        start_time=start,
        end_time=slot.end_time,
        party_size=body.party_size,
        guest_name=current_user.name or "Guest",
        guest_phone=current_user.phone or "",
        notes=body.notes,
    )
    db.add(reservation)
    await db.commit()
    return {
        "reservation": {
            "id": reservation.id,
            "date": reservation.reservation_date.isoformat(),
            "start_time": reservation.start_time.isoformat() if reservation.start_time else None,
        }
    }


@router.get("/customer/me/reservations")
async def my_reservations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.user_id == current_user.id)
        .order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc())
        .limit(20)
    )
    reservations = result.scalars().all()
    return {
        "reservations": [
            {
                "id": r.id,
                "date": r.reservation_date.isoformat(),
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "party_size": r.party_size,
                "status": r.status,
                "notes": r.notes,
            }
            for r in reservations
        ]
    }
