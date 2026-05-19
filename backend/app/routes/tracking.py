"""QR scan tracking and consent routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_customer
from app.models import QRScanEvent, User, UserNotificationPreference
from datetime import datetime, timezone

router = APIRouter()


# --- QR Scan Tracking ---

@router.post("/tracking/qr-scan-confirmed")
async def confirm_qr_scan(
    request: Request,
    campaign_id: str | None = None,
    source_code: str | None = None,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Client-side beacon: confirms a real QR scan after page render."""
    user_agent = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else "unknown"
    from app.services.auth_service import hash_ip

    event = QRScanEvent(
        qr_campaign_id=campaign_id,
        source_code=source_code,
        anonymous_session_id=session_id,
        event_type="scan_confirmed",
        user_agent=user_agent,
        ip_hash=hash_ip(ip),
        is_likely_bot=False,
    )
    db.add(event)
    await db.commit()
    return {"ok": True}


# --- Consent ---

@router.post("/consent/preferences")
async def update_consent(
    sms_marketing_opt_in: bool | None = None,
    push_enabled: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    result = await db.execute(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = UserNotificationPreference(user_id=current_user.id)
        db.add(prefs)

    if sms_marketing_opt_in is not None:
        prefs.sms_marketing_opt_in = sms_marketing_opt_in
        if sms_marketing_opt_in:
            prefs.consent_source = "api"
            prefs.consented_at = datetime.now(timezone.utc)
            prefs.unsubscribed_at = None
        else:
            prefs.unsubscribed_at = datetime.now(timezone.utc)

    if push_enabled is not None:
        prefs.push_enabled = push_enabled

    await db.commit()
    return {"ok": True}


# --- Unsubscribe ---

@router.get("/consent/unsubscribe/{token}")
async def unsubscribe(token: str, db: AsyncSession = Depends(get_db)):
    """One-click unsubscribe web page."""
    from app.models import ShortLink

    result = await db.execute(select(ShortLink).where(ShortLink.code == token))
    link = result.scalar_one_or_none()
    if not link or link.link_type != "unsubscribe":
        return {"ok": False, "message": "Invalid unsubscribe link"}

    if link.user_id:
        result = await db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == link.user_id
            )
        )
        prefs = result.scalar_one_or_none()
        if prefs:
            prefs.sms_marketing_opt_in = False
            prefs.unsubscribed_at = datetime.now(timezone.utc)
            await db.commit()

    return {"ok": True, "message": "You have been unsubscribed from marketing messages."}
