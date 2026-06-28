from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSession, get_db
from app.models import RefreshToken, User
from app.schemas.common import AdminLoginRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from datetime import datetime, timedelta, timezone

router = APIRouter()
settings = get_settings()

ACCESS_TOKEN_MAX_AGE = 60 * 15
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
        )
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
