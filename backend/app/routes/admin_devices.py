import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import Device, User
from app.services.auth_service import hash_otp

router = APIRouter(prefix="/api/admin", tags=["admin-devices"])


class CreateDeviceRequest(BaseModel):
    name: str
    location: str | None = None


def generate_pin() -> str:
    return f"{secrets.randbelow(10000):04d}"


@router.get("/devices")
async def list_devices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(
        select(Device).where(Device.is_active == True).order_by(Device.created_at.desc())
    )
    devices = result.scalars().all()
    return {
        "data": [
            {
                "id": d.id,
                "name": d.name,
                "location": d.location,
                "status": d.status,
                "paired_at": d.paired_at.isoformat() if d.paired_at else None,
                "created_at": d.created_at.isoformat(),
            }
            for d in devices
        ]
    }


@router.post("/devices")
async def create_device(
    body: CreateDeviceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin(["owner", "manager"])),
):
    pin = generate_pin()
    device = Device(
        name=body.name,
        pin_hash=hash_otp(pin),
        location=body.location,
        created_by=user.id,
    )
    db.add(device)
    await db.commit()
    return {"data": {"id": device.id, "name": device.name, "pin": pin, "status": device.status}}


@router.delete("/devices/{device_id}")
async def deactivate_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.is_active = False
    await db.commit()
    return {"data": {"id": device.id, "status": "deactivated"}}
