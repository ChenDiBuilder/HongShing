"""Admin settings and notification routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import (
    Notification,
    RestaurantSettings,
    User,
    UserNotificationPreference,
)

router = APIRouter()


# --- Settings ---

@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(select(RestaurantSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = RestaurantSettings(id="00000000-0000-0000-0000-000000000001")
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return {
        "data": {
            "restaurant_name": settings.restaurant_name,
            "primary_color": settings.primary_color,
            "secondary_color": settings.secondary_color,
            "logo_url": settings.logo_url,
            "external_ordering_url": settings.external_ordering_url,
            "external_ordering_provider": settings.external_ordering_provider,
            "allow_order_without_signup": settings.allow_order_without_signup,
            "default_reward_template_id": settings.default_reward_template_id,
            "timezone": settings.timezone,
            "privacy_contact_email": settings.privacy_contact_email,
            "support_phone": settings.support_phone,
        }
    }


@router.patch("/settings")
async def update_settings(
    restaurant_name: str | None = None,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    external_ordering_url: str | None = None,
    external_ordering_provider: str | None = None,
    allow_order_without_signup: bool | None = None,
    default_reward_template_id: str | None = None,
    privacy_contact_email: str | None = None,
    support_phone: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    result = await db.execute(select(RestaurantSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = RestaurantSettings(id="00000000-0000-0000-0000-000000000001")
        db.add(settings)

    if restaurant_name is not None:
        settings.restaurant_name = restaurant_name
    if primary_color is not None:
        settings.primary_color = primary_color
    if secondary_color is not None:
        settings.secondary_color = secondary_color
    if external_ordering_url is not None:
        settings.external_ordering_url = external_ordering_url
    if external_ordering_provider is not None:
        settings.external_ordering_provider = external_ordering_provider
    if allow_order_without_signup is not None:
        settings.allow_order_without_signup = allow_order_without_signup
    if default_reward_template_id is not None:
        settings.default_reward_template_id = default_reward_template_id
    if privacy_contact_email is not None:
        settings.privacy_contact_email = privacy_contact_email
    if support_phone is not None:
        settings.support_phone = support_phone

    await db.commit()
    return {"ok": True}


# --- Notifications ---

@router.post("/notifications/sms")
async def send_sms(
    recipient_id: str | None = None,
    title: str | None = None,
    body: str = "",
    message_type: str = "marketing",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager"])),
):
    # Check consent for marketing
    if message_type == "marketing" and recipient_id:
        result = await db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == recipient_id
            )
        )
        prefs = result.scalar_one_or_none()
        if prefs and not prefs.sms_marketing_opt_in:
            raise HTTPException(status_code=400, detail="Customer has not opted in to marketing SMS")

    notification = Notification(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        title=title,
        body=body,
        channel="sms",
        message_type=message_type,
        status="sent",
    )
    db.add(notification)
    await db.commit()

    # TODO: Send via AWS SNS

    return {"ok": True, "id": notification.id}


@router.get("/notifications")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner", "manager", "staff"])),
):
    result = await db.execute(
        select(Notification).order_by(Notification.created_at.desc()).limit(50)
    )
    items = result.scalars().all()
    return {
        "data": [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "channel": n.channel,
                "message_type": n.message_type,
                "status": n.status,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in items
        ]
    }
