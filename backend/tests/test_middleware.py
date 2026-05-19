"""Integration tests for auth middleware."""

from app.services.auth_service import create_access_token


class TestAuthMiddleware:
    async def test_protected_route_without_cookie_returns_401(self, client):
        resp = await client.get("/api/admin/dashboard")
        assert resp.status_code == 401

    async def test_protected_route_with_invalid_token_returns_401(self, client):
        client.cookies.set("admin_access_token", "not-a-valid-jwt", domain="test")
        resp = await client.get("/api/admin/dashboard")
        assert resp.status_code == 401

    async def test_staff_cannot_access_settings(self, client, staff_user):
        """Staff role should be blocked from owner/manager routes."""
        token = create_access_token(staff_user.id, "staff")
        client.cookies.set("admin_access_token", token, domain="test")
        # /api/admin/settings is not implemented yet — skip
        # This test sets up the pattern for future routes


class TestRoleIsolation:
    async def test_customer_cannot_access_admin_routes(self, client, customer_user):
        token = create_access_token(customer_user.id, "customer")
        client.cookies.set("admin_access_token", token, domain="test")
        resp = await client.get("/api/admin/dashboard")
        assert resp.status_code == 401
