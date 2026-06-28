"""Admin seed mock data endpoint."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSession, get_db
from app.middleware.auth import require_admin
from app.models import User

router = APIRouter()

MENU_ITEMS = [
    ("General Tao Chicken", 1895),
    ("Chili Chicken", 1695),
    ("Ma La Wings", 1495),
    ("Garlic Beef Tenderloin", 2195),
    ("Spicy Shrimps", 1895),
    ("Hong Shing Fried Rice", 1495),
    ("Crispy Beef", 1795),
    ("XO Seafood Fried Rice", 2195),
    ("Honey Garlic Wings", 1395),
    ("Ginger Scallion Cod", 2395),
    ("Kung Pao Chicken", 1695),
    ("Mapo Tofu", 1395),
    ("Salt and Pepper Squid", 1795),
    ("Beef Chow Mein", 1595),
    ("Yang Chow Fried Rice", 1495),
]

SOURCES = ["receipt", "takeout_bag", "counter", "instagram", "website"]


@router.post("/seed-mock-data")
async def seed_mock_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin(["owner"])),
):
    # Mock data must never be injectable into a real restaurant's dashboard.
    if get_settings().app_env == "production":
        raise HTTPException(status_code=403, detail="Mock seeding is disabled in production")

    now = datetime.now(timezone.utc)

    count = await db.scalar(
        text("SELECT COUNT(*) FROM qr_scan_events WHERE event_type = :et"),
        {"et": "scan_confirmed"},
    )
    if count > 0:
        return {"ok": False, "message": f"Already has {count} mock scans"}

    customer_ids = []
    phones = []
    for i in range(25):
        uid = str(uuid.uuid4())
        phone = f"+1647{i:07d}"[-12:]
        phones.append(phone)
        customer_ids.append(uid)
        await db.execute(
            text("INSERT INTO users (id, phone, role, created_at, updated_at) VALUES (:id, :phone, 'customer', :ts, :ts)"),
            {"id": uid, "phone": phone, "ts": now - timedelta(days=i * 2, hours=i * 3)},
        )

    campaign_ids = {}
    for src in SOURCES:
        existing = await db.scalar(
            text("SELECT id FROM qr_campaigns WHERE source_code = :src"), {"src": src}
        )
        if existing:
            campaign_ids[src] = existing
        else:
            cid = str(uuid.uuid4())
            campaign_ids[src] = cid
            await db.execute(
                text("INSERT INTO qr_campaigns (id, name, source_code, active, created_at, updated_at) VALUES (:id, :name, :src, true, :ts, :ts)"),
                {"id": cid, "name": f"Campaign: {src}", "src": src, "ts": now - timedelta(days=30)},
            )
    await db.flush()

    for day_offset in range(14):
        day = now - timedelta(days=day_offset)
        num_scans = 5 + (day_offset % 5) * 3
        for k in range(num_scans):
            src = SOURCES[k % len(SOURCES)]
            await db.execute(
                text("INSERT INTO qr_scan_events (id, qr_campaign_id, source_code, event_type, user_agent, is_likely_bot, created_at) VALUES (:id, :cid, :src, :et, :ua, false, :ts)"),
                {"id": str(uuid.uuid4()), "cid": campaign_ids[src], "src": src,
                 "et": "scan_confirmed", "ua": "Mozilla/5.0 (iPhone)",
                 "ts": day.replace(hour=10 + (k % 12), minute=(k * 7) % 60)},
            )

    for day_offset in range(14):
        day = now - timedelta(days=day_offset)
        num_signups = max(1, 3 + day_offset % 4)
        for j in range(num_signups):
            idx = (day_offset * 4 + j) % len(customer_ids)
            src = SOURCES[(day_offset + j) % len(SOURCES)]
            await db.execute(
                text("INSERT INTO signup_events (id, user_id, phone, source_code, qr_campaign_id, signup_method, marketing_opt_in, created_at) VALUES (:id, :uid, :phone, :src, :cid, 'qr', false, :ts)"),
                {"id": str(uuid.uuid4()), "uid": customer_ids[idx], "phone": phones[idx],
                 "src": src, "cid": campaign_ids[src],
                 "ts": day.replace(hour=10 + j * 2, minute=(j * 15) % 60)},
            )

    for day_offset in range(14):
        day = now - timedelta(days=day_offset)
        num_orders = max(1, 2 + day_offset % 3)
        for j in range(num_orders):
            idx = (day_offset * 3 + j) % len(customer_ids)
            oid = str(uuid.uuid4())
            num_items = 1 + (j % 3)
            total = 0
            item_count = 0
            order_ts = day.replace(hour=11 + j * 3, minute=j * 10)

            statuses = ["confirmed", "preparing", "ready", "picked_up", "cancelled"]
            status = "picked_up" if day_offset > 2 else statuses[j % 4]

            await db.execute(
                text("INSERT INTO orders (id, user_id, subtotal_cents, total_cents, item_count, status, created_at, updated_at) VALUES (:id, :uid, :total, :total, :cnt, :status, :ts, :ts)"),
                {"id": oid, "uid": customer_ids[idx], "total": total, "cnt": item_count, "status": status, "ts": order_ts},
            )

            for k in range(num_items):
                item_idx = (day_offset * 5 + j * 3 + k) % len(MENU_ITEMS)
                name, price = MENU_ITEMS[item_idx]
                qty = 1 + (k % 2)
                total += price * qty
                item_count += qty
                await db.execute(
                    text("INSERT INTO order_items (id, order_id, name, price_cents, quantity, created_at) VALUES (:id, :oid, :name, :price, :qty, :ts)"),
                    {"id": str(uuid.uuid4()), "oid": oid, "name": name, "price": price, "qty": qty, "ts": order_ts},
                )

            # Correct both subtotal and total after the item loop (total is 0 at INSERT
            # time). Mock orders carry no reward/tax, so subtotal == total.
            await db.execute(
                text("UPDATE orders SET subtotal_cents = :total, total_cents = :total, item_count = :cnt WHERE id = :oid"),
                {"oid": oid, "total": total, "cnt": item_count},
            )

    rt_id = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO reward_templates (id, name, code_prefix, reward_type, reward_value, max_uses_per_user, valid_days, active, created_at, updated_at) VALUES (:id, :name, 'HS', 'fixed', 500, 1, 30, true, :ts, :ts)"),
        {"id": rt_id, "name": "$5 Off", "ts": now - timedelta(days=30)},
    )
    await db.commit()

    reward_ids = []
    for i in range(min(18, len(customer_ids))):
        rid = str(uuid.uuid4())
        code = f"HS-{uuid.uuid4().hex[:6].upper()}"
        src = SOURCES[i % len(SOURCES)]
        status = "redeemed" if i < 5 else "issued"
        issued_at = now - timedelta(days=i * 2, hours=5)
        redeemed_at = issued_at + timedelta(hours=3) if status == "redeemed" else None
        await db.execute(
            text("INSERT INTO rewards (id, user_id, reward_template_id, code, source_code, qr_campaign_id, status, issued_at, expires_at, redeemed_at, redemption_source) VALUES (:id, :uid, :rtid, :code, :src, :cid, :status, :issued, :expires, :redeemed, :rsrc)"),
            {"id": rid, "uid": customer_ids[i], "rtid": rt_id, "code": code,
             "src": src, "cid": campaign_ids[src], "status": status,
             "issued": issued_at, "expires": issued_at + timedelta(days=30),
             "redeemed": redeemed_at, "rsrc": "manual" if status == "redeemed" else None},
        )
        reward_ids.append(rid)

    for i in range(min(12, len(reward_ids))):
        src = SOURCES[i % len(SOURCES)]
        await db.execute(
            text("INSERT INTO external_order_redirects (id, user_id, reward_id, source_code, qr_campaign_id, destination_url, provider, created_at) VALUES (:id, :uid, :rid, :src, :cid, :url, 'demo', :ts)"),
            {"id": str(uuid.uuid4()), "uid": customer_ids[i], "rid": reward_ids[i],
             "src": src, "cid": campaign_ids[src],
             "url": "https://hongshing.ca/order",
             "ts": now - timedelta(days=i, hours=i * 2)},
        )

    for i in range(15):
        # email_marketing_opt_in / push_enabled are NOT NULL with Python-only defaults
        # (no server_default), so a raw INSERT must set them explicitly or it 500s.
        await db.execute(
            text("INSERT INTO user_notification_preferences (id, user_id, sms_marketing_opt_in, sms_transactional_enabled, email_marketing_opt_in, push_enabled, updated_at) VALUES (:id, :uid, :opt, true, false, false, :ts) ON CONFLICT (user_id) DO UPDATE SET sms_marketing_opt_in = :opt2"),
            {"id": str(uuid.uuid4()), "uid": customer_ids[i], "opt": i < 8, "opt2": i < 8, "ts": now},
        )

    await db.commit()
    return {
        "ok": True,
        "message": "Seed complete: 25 customers, 5 campaigns, ~140 scans, ~55 signups, ~42 orders, 18 rewards, 12 redirects",
    }
