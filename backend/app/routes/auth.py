from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.config import get_settings
from app.models import RefreshToken, User
from app.schemas.common import (
    SendOTPRequest,
    TokenResponse,
    UserResponse,
    VerifyOTPRequest,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_token,
)

router = APIRouter()
settings = get_settings()

ACCESS_TOKEN_MAX_AGE = 60 * 15
REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 30


@router.post("/send-otp", status_code=202)
async def send_otp(body: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    import secrets

    from app.models import OTPCode
    from app.services.auth_service import hash_otp
    from app.services.sms_service import send_sms

    now = datetime.now(timezone.utc)

    # Anti-abuse / SMS-cost control: 30s resend cooldown + max 5/hour per phone.
    recent = await db.execute(
        select(OTPCode)
        .where(OTPCode.phone == body.phone, OTPCode.created_at > now - timedelta(hours=1))
        .order_by(OTPCode.created_at.desc())
    )
    recent_rows = recent.scalars().all()
    if recent_rows:
        if (now - recent_rows[0].created_at).total_seconds() < 30:
            raise HTTPException(status_code=429, detail="Please wait before requesting another code")
        if len(recent_rows) >= 5:
            raise HTTPException(status_code=429, detail="Too many code requests. Try again later.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        OTPCode(
            phone=body.phone,
            code_hash=hash_otp(code),
            expires_at=now + timedelta(seconds=300),
        )
    )
    await db.commit()

    # Demo mode (hardcoded_otp set): verify-otp accepts the hardcoded code, so
    # skip the real SMS send and its cost — the generated code is still stored.
    # send_sms swallows SNS errors (sandbox/missing creds); the code is already
    # persisted, so verify-otp works even when delivery is unavailable.
    if not settings.hardcoded_otp:
        send_sms(body.phone, f"Your HongShing verification code is {code}. It expires in 5 minutes.")
    return {"ok": True, "message": "OTP sent"}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: VerifyOTPRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    if settings.hardcoded_otp:
        if body.code != settings.hardcoded_otp:
            raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    else:
        from app.models import OTPCode
        from app.services.auth_service import hash_otp

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

    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        user = User(phone=body.phone, role="customer")
        db.add(user)
        await db.flush()

    if is_new_user:
        from app.models import SignupEvent

        signup = SignupEvent(
            user_id=user.id,
            phone=body.phone,
            source_code=body.source_code,
            qr_campaign_id=body.campaign_id,
            signup_method="qr",
            marketing_opt_in=body.marketing_opt_in,
        )
        db.add(signup)

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


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"ok": True}

