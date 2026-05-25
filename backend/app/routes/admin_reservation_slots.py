from datetime import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import ReservationSlot, User

router = APIRouter(prefix="/api/admin", tags=["admin-reservation-slots"])


class CreateSlotRequest(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    max_party_size: int = 6
    max_reservations: int = 4


@router.get("/reservation-slots")
async def list_slots(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(
        select(ReservationSlot).order_by(ReservationSlot.day_of_week, ReservationSlot.start_time)
    )
    slots = result.scalars().all()
    return {
        "data": [
            {
                "id": s.id,
                "day_of_week": s.day_of_week,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "max_party_size": s.max_party_size,
                "max_reservations": s.max_reservations,
                "is_active": s.is_active,
            }
            for s in slots
        ]
    }


@router.post("/reservation-slots")
async def create_slot(
    body: CreateSlotRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin(["owner", "manager"])),
):
    if body.day_of_week < 0 or body.day_of_week > 6:
        raise HTTPException(status_code=400, detail="day_of_week must be 0-6")
    start_parts = body.start_time.split(":")
    end_parts = body.end_time.split(":")
    slot = ReservationSlot(
        day_of_week=body.day_of_week,
        start_time=time(int(start_parts[0]), int(start_parts[1])),
        end_time=time(int(end_parts[0]), int(end_parts[1])),
        max_party_size=body.max_party_size,
        max_reservations=body.max_reservations,
    )
    db.add(slot)
    await db.commit()
    return {"data": {"id": slot.id, "day_of_week": slot.day_of_week}}


@router.patch("/reservation-slots/{slot_id}")
async def update_slot(
    slot_id: str,
    body: CreateSlotRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(select(ReservationSlot).where(ReservationSlot.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    start_parts = body.start_time.split(":")
    end_parts = body.end_time.split(":")
    slot.day_of_week = body.day_of_week
    slot.start_time = time(int(start_parts[0]), int(start_parts[1]))
    slot.end_time = time(int(end_parts[0]), int(end_parts[1]))
    slot.max_party_size = body.max_party_size
    slot.max_reservations = body.max_reservations
    await db.commit()
    return {"data": {"id": slot.id}}


@router.delete("/reservation-slots/{slot_id}")
async def delete_slot(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(select(ReservationSlot).where(ReservationSlot.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    slot.is_active = False
    await db.commit()
    return {"data": {"id": slot.id, "status": "deactivated"}}
