from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.models import Device, User
from app.services.auth_service import decode_token


def require_admin(allowed_roles: list[str]) -> Callable:
    """Dependency factory: validates admin JWT from cookie and checks role."""

    async def _require_admin(
        request: Request, db: AsyncSession = Depends(get_db)
    ) -> User:
        token = request.cookies.get("admin_access_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        try:
            payload = decode_token(token)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user_id = payload.get("sub")
        role = payload.get("role")

        if role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return user

    return _require_admin


async def require_customer(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Validates customer JWT from cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def require_device(request: Request, db: AsyncSession = Depends(get_db)) -> Device:
    """Validates storefront device JWT from cookie."""
    token = request.cookies.get("storefront_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "device_access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    device_id = payload.get("sub")
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.is_active == True)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device not found")

    return device
