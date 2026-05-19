import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.config import get_settings
from app.models import OTPCode, RefreshToken, User
from app.schemas.common import (
    SendOTPRequest,
    TokenResponse,
    UserResponse,
    VerifyOTPRequest,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_otp,
    hash_phone,
    hash_token,
)
from app.services.sms_service import send_sms

router = APIRouter()

ACCESS_TOKEN_MAX_AGE = 60 * 15
REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 30


@router.post("/send-otp", status_code=202)
async def send_otp(body: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    # Generate OTP
    otp = secrets.randbelow(1_000_000)
    otp_str = f"{otp:06d}"
    code_hash = hash_otp(otp_str)

    otp_code = OTPCode(
        phone=body.phone,
        code_hash=code_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(otp_code)
    await db.commit()

    # Store plaintext OTP for E2E retrieval via /api/test/sms-messages
    from app.models.test_sms import TestSmsMessage

    test_msg = TestSmsMessage(phone=body.phone, otp_code=otp_str)
    db.add(test_msg)
    await db.commit()

    # Send OTP via AWS SNS (falls back to console log if SNS unavailable/sandboxed)
    message = f"Your Hong Shing verification code is: {otp_str}"
    send_sms(body.phone, message)

    return {"ok": True, "message": "OTP sent"}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: VerifyOTPRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    code_hash = hash_otp(body.code)

    result = await db.execute(
        select(OTPCode)
        .where(
            OTPCode.phone == body.phone,
            OTPCode.code_hash == code_hash,
            OTPCode.consumed == False,  # noqa: E712
            OTPCode.expires_at > datetime.now(timezone.utc),
        )
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    )
    otp_code = result.scalar_one_or_none()

    if not otp_code:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    if otp_code.attempt_count >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    otp_code.attempt_count += 1
    await db.flush()

    otp_code.consumed = True
    otp_code.consumed_at = datetime.now(timezone.utc)

    # Find or create user
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    if not user:
        user = User(phone=body.phone, role="customer")
        db.add(user)
        await db.flush()

    # Create tokens
    access_token = create_access_token(user.id, user.role)
    refresh_token_str = create_refresh_token(user.id, user.role)

    refresh_db = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_MAX_AGE),
    )
    db.add(refresh_db)
    await db.commit()
    await db.refresh(user)

    # Set HttpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        max_age=REFRESH_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/auth",
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
async def refresh_token(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    refresh_token_str = request.cookies.get("refresh_token")
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
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_MAX_AGE),
    )
    db.add(new_refresh)
    await db.commit()

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_str,
        max_age=REFRESH_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/auth",
    )

    return {"ok": True}

