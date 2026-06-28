"""Admin auth hardening (SCRUM-73): temp-password enforcement + role-vs-DB."""

from app.models import User
from app.services.auth_service import create_access_token, hash_password


class TestTempPassword:
    async def test_login_flags_must_change_when_never_rotated(self, client, db_session):
        db_session.add(User(email="o@x.com", name="O", password_hash=hash_password("temp1234"), role="owner"))
        await db_session.flush()
        r = await client.post("/api/admin/auth/login", json={"email": "o@x.com", "password": "temp1234"})
        assert r.status_code == 200
        assert r.json()["must_change_password"] is True

    async def test_change_password_validates_and_clears_flag(self, client, db_session):
        db_session.add(User(email="o2@x.com", name="O2", password_hash=hash_password("temp1234"), role="owner"))
        u = (await db_session.flush()) or None  # flush; fetch below
        from sqlalchemy import select
        u = (await db_session.execute(select(User).where(User.email == "o2@x.com"))).scalar_one()
        client.cookies.set("admin_access_token", create_access_token(u.id, "owner"))

        bad = await client.post("/api/admin/auth/change-password", json={"current_password": "nope", "new_password": "longenough1"})
        assert bad.status_code == 401
        short = await client.post("/api/admin/auth/change-password", json={"current_password": "temp1234", "new_password": "short"})
        assert short.status_code == 400
        ok = await client.post("/api/admin/auth/change-password", json={"current_password": "temp1234", "new_password": "newlongpass1"})
        assert ok.status_code == 200

        r = await client.post("/api/admin/auth/login", json={"email": "o2@x.com", "password": "newlongpass1"})
        assert r.status_code == 200
        assert r.json()["must_change_password"] is False


class TestRoleVsDb:
    async def test_stale_owner_token_rejected_after_downgrade(self, client, db_session):
        # DB role is staff, but a stale token still claims owner.
        db_session.add(User(email="s@x.com", name="S", password_hash=hash_password("x"), role="staff"))
        from sqlalchemy import select
        await db_session.flush()
        u = (await db_session.execute(select(User).where(User.email == "s@x.com"))).scalar_one()
        client.cookies.set("admin_access_token", create_access_token(u.id, "owner"))
        # owner-only endpoint must reject based on the live DB role
        r = await client.post("/api/admin/seed-mock-data")
        assert r.status_code == 403
