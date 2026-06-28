from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSession, get_db
from app.middleware.auth import require_device
from app.models import Device
from app.services.auth_service import create_access_token, hash_otp

router = APIRouter(prefix="/api/storefront/auth", tags=["storefront-auth"])
settings = get_settings()

DEVICE_ACCESS_TOKEN_MAX_AGE = 60 * 60 * 12


class DeviceLoginRequest(BaseModel):
    pin: str


@router.post("/login")
async def device_login(
    body: DeviceLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    pin_hash = hash_otp(body.pin)

    result = await db.execute(
        select(Device)
        .where(Device.pin_hash == pin_hash, Device.is_active == True)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid PIN")

    if device.status != "unpaired":
        raise HTTPException(status_code=401, detail="This PIN has already been used")

    device.status = "paired"
    device.paired_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(
        user_id=device.id,
        role="device",
        token_type="device_access",
        max_age=DEVICE_ACCESS_TOKEN_MAX_AGE,
    )
    response.set_cookie(
        key="storefront_token",
        value=token,
        max_age=DEVICE_ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return {
        "device": {
            "id": device.id,
            "name": device.name,
            "location": device.location,
        }
    }


@router.post("/logout")
async def device_logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device),
):
    device.status = "unpaired"
    device.paired_at = None
    await db.commit()

    response.delete_cookie("storefront_token", path="/")
    return {"ok": True}
