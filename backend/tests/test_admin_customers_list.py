"""Tests for the customer-list value columns (SCRUM-243)."""

from datetime import datetime, timedelta, timezone

from app.models import Order, User
from app.services.auth_service import create_access_token


class TestCustomerListValueColumns:
    async def test_visits_avg_ticket_last_seen(self, client, owner_user, db_session):
        now = datetime.now(timezone.utc)
        regular = User(phone="+14035550101", name="Regular", role="customer")
        ghost = User(phone="+14035550102", name="Ghost", role="customer")
        db_session.add_all([regular, ghost])
        await db_session.flush()

        for cents, days_ago, status in ((4_000, 9.0, "picked_up"), (6_000, 2.0, "picked_up"), (99_999, 1.0, "cancelled")):
            db_session.add(
                Order(
                    user_id=regular.id,
                    subtotal_cents=cents,
                    discount_cents=0,
                    tax_cents=0,
                    total_cents=cents,
                    item_count=1,
                    status=status,
                    created_at=now - timedelta(days=days_ago),
                )
            )
        await db_session.commit()

        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/customers")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        by_phone = {i["phone"]: i for i in items}

        r = by_phone["+14035550101"]
        assert r["visits"] == 2  # cancelled order doesn't count
        assert r["avg_ticket_cents"] == 5_000
        assert r["last_order_at"] is not None

        g = by_phone["+14035550102"]
        assert g["visits"] == 0
        assert g["avg_ticket_cents"] is None
        assert g["last_order_at"] is None

        # most-recently-seen first; never-ordered customers sort last
        assert items[0]["phone"] == "+14035550101"
        assert items[-1]["phone"] == "+14035550102"

    async def test_search_still_works(self, client, owner_user, db_session):
        db_session.add(User(phone="+14035550777", name="Searchable Sam", role="customer"))
        await db_session.commit()

        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.get("/api/admin/customers?search=Searchable")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Searchable Sam"
        assert items[0]["visits"] == 0
