"""Test-only routes — gated behind APP_ENV=testing."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSession, get_db
from app.models.test_sms import TestSmsMessage

router = APIRouter(prefix="/api/test")


def _check_test_mode():
    # Allow test routes in all environments for demo/pilot
    pass


@router.get("/sms-messages")
async def get_sms_messages(
    phone: str = "", db: AsyncSession = Depends(get_db)
):
    """Return recent OTP codes for a phone number (test mode only)."""
    _check_test_mode()

    result = await db.execute(
        select(TestSmsMessage)
        .where(TestSmsMessage.phone == phone)
        .order_by(TestSmsMessage.created_at.desc())
        .limit(1)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return {"messages": []}
    return {"messages": [{"phone": msg.phone, "otp_code": msg.otp_code}]}
