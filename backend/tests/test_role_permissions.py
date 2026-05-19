"""Unit tests for role permission matrix — no database or HTTP."""

# Permission matrix matching the spec
PERMISSIONS = {
    "owner": {
        "manage_settings", "create_admin_accounts", "view_dashboard",
        "manage_qr_campaigns", "manage_reward_templates", "mark_reward_redeemed",
        "view_customers", "export_customers", "send_marketing_sms", "update_customer_notes",
    },
    "manager": {
        "manage_settings", "view_dashboard",
        "manage_qr_campaigns", "manage_reward_templates", "mark_reward_redeemed",
        "view_customers", "export_customers", "send_marketing_sms", "update_customer_notes",
    },
    "staff": {
        "view_dashboard", "mark_reward_redeemed", "view_customers", "update_customer_notes",
    },
    "customer": set(),
}


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


class TestRolePermissions:
    def test_owner_has_full_access(self):
        for perm in PERMISSIONS["owner"]:
            assert has_permission("owner", perm)

    def test_manager_cannot_create_admin_accounts(self):
        assert not has_permission("manager", "create_admin_accounts")

    def test_manager_can_manage_settings(self):
        assert has_permission("manager", "manage_settings")

    def test_staff_cannot_manage_settings(self):
        assert not has_permission("staff", "manage_settings")

    def test_staff_cannot_export_customers(self):
        assert not has_permission("staff", "export_customers")

    def test_staff_cannot_send_marketing_sms(self):
        assert not has_permission("staff", "send_marketing_sms")

    def test_staff_can_view_dashboard(self):
        assert has_permission("staff", "view_dashboard")

    def test_staff_can_mark_reward_redeemed(self):
        assert has_permission("staff", "mark_reward_redeemed")

    def test_staff_can_view_customers(self):
        assert has_permission("staff", "view_customers")

    def test_customer_has_no_admin_permissions(self):
        for perm in PERMISSIONS["owner"]:
            assert not has_permission("customer", perm)

    def test_unknown_role_has_no_permissions(self):
        assert not has_permission("nobody", "view_dashboard")
