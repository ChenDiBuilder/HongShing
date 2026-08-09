"""Integration tests for admin reservation-slot routes (SCRUM-241)."""

from app.services.auth_service import create_access_token


class TestAdminReservationSlots:
    async def test_create_and_list(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.post(
            "/api/admin/reservation-slots",
            json={"day_of_week": 5, "start_time": "17:00", "end_time": "17:30"},
        )
        assert resp.status_code == 200
        slot_id = resp.json()["data"]["id"]

        resp = await client.get("/api/admin/reservation-slots")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["data"]]
        assert slot_id in ids

    async def test_deleted_slot_leaves_the_list(self, client, owner_user):
        token = create_access_token(owner_user.id, "owner")
        client.cookies.set("admin_access_token", token)
        resp = await client.post(
            "/api/admin/reservation-slots",
            json={"day_of_week": 6, "start_time": "18:00", "end_time": "18:30"},
        )
        slot_id = resp.json()["data"]["id"]

        resp = await client.delete(f"/api/admin/reservation-slots/{slot_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "deactivated"

        # Soft-deleted slots must not resurface in the admin list — before this
        # filter, Remove looked broken because the row came back on reload.
        resp = await client.get("/api/admin/reservation-slots")
        ids = [s["id"] for s in resp.json()["data"]]
        assert slot_id not in ids
