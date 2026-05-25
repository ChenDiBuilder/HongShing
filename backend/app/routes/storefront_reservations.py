from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_device
from app.models import Device, Reservation

router = APIRouter(prefix="/api/storefront", tags=["storefront"])


class UpdateReservationStatusRequest(BaseModel):
    status: str


@router.get("/reservations")
async def list_reservations(
    reservation_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device),
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.reservation_date == reservation_date)
        .order_by(Reservation.start_time.asc())
        .limit(100)
    )
    reservations = result.scalars().all()
    return {
        "reservations": [
            {
                "id": r.id,
                "guest_name": r.guest_name,
                "guest_phone": r.guest_phone,
                "party_size": r.party_size,
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "status": r.status,
                "notes": r.notes,
                "created_at": r.created_at.isoformat(),
            }
            for r in reservations
        ]
    }


@router.patch("/reservations/{reservation_id}/status")
async def update_reservation_status(
    reservation_id: str,
    body: UpdateReservationStatusRequest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device),
):
    if body.status not in ("confirmed", "arrived", "seated", "cancelled", "no_show"):
        raise HTTPException(status_code=400, detail="Invalid status")

    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation.status = body.status
    await db.commit()
    return {"ok": True, "status": body.status}
