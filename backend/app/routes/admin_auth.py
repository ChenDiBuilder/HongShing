from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select, update

from app.config import get_settings
from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import RefreshToken, User
from app.schemas.common import AdminLoginRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from datetime import datetime, timedelta, timezone

ADMIN_ROLES = ["owner", "manager", "staff"]

router = APIRouter()
settings = get_settings()

# Admin access-token lifetime. Bumped 15min -> 2h (Daniel, 2026-08-08): the SPA
# does not yet auto-refresh on 401 (the 12h refresh token is issued but unused by
# the frontend), so the effective session == this value. 15min was timing admins
# out mid-task / mid-demo; 2h is a comfortable working session. The real fix
# (wire /refresh into the SPA for the full rolling 12h) is tracked separately.
ACCESS_TOKEN_MAX_AGE = 60 * 60 * 2
ADMIN_REFRESH_MAX_AGE = 60 * 60 * 12


@router.post("/login", response_model=TokenResponse)
async def admin_login(
    body: AdminLoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(
            User.email == body.email,
            User.role.in_(["owner", "manager", "staff"]),
        )
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user.id, user.role)
    refresh_token_str = create_refresh_token(user.id, user.role)

    refresh_db = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ADMIN_REFRESH_MAX_AGE),
    )
    db.add(refresh_db)
    await db.commit()

    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="admin_refresh_token",
        value=refresh_token_str,
        max_age=ADMIN_REFRESH_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/admin/auth",
    )

    return TokenResponse(
        user=UserResponse(
            id=user.id,
            phone=user.phone,
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
        ),
        # A provisioned owner has password_changed_at=None until they rotate the
        # temp password; the frontend uses this to force a change before access.
        must_change_password=user.password_changed_at is None,
    )


@router.post("/refresh")
async def admin_refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    refresh_token_str = request.cookies.get("admin_refresh_token")
    if not refresh_token_str:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_hash = hash_token(refresh_token_str)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    stored_token = result.scalar_one_or_none()

    if not stored_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    stored_token.revoked = True

    result = await db.execute(select(User).where(User.id == stored_token.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(user.id, user.role)
    new_refresh_str = create_refresh_token(user.id, user.role)

    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_str),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ADMIN_REFRESH_MAX_AGE),
    )
    db.add(new_refresh)
    await db.commit()

    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="admin_refresh_token",
        value=new_refresh_str,
        max_age=ADMIN_REFRESH_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/admin/auth",
    )

    return {"ok": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def admin_change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(ADMIN_ROLES)),
):
    """Set a new admin password and stamp password_changed_at (clears the
    force-change state). Also revokes outstanding refresh tokens so other
    sessions can't keep riding the old credential."""
    if not current_user.password_hash or not verify_password(
        body.current_password, current_user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one")

    current_user.password_hash = hash_password(body.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id, RefreshToken.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    await db.commit()
    return {"ok": True}


@router.post("/logout")
async def admin_logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Revoke the presented refresh token and clear the admin cookies."""
    refresh_token_str = request.cookies.get("admin_refresh_token")
    if refresh_token_str:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(refresh_token_str))
            .values(revoked=True)
        )
        await db.commit()
    response.delete_cookie("admin_access_token", path="/")
    response.delete_cookie("admin_refresh_token", path="/api/admin/auth")
    return {"ok": True}
