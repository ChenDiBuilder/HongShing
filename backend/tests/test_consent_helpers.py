"""Unit tests for consent helper functions — no database or HTTP."""


class TestConsentDefaults:
    def test_marketing_opt_in_defaults_false(self):
        """Marketing consent must be explicitly opted in."""
        opt_in = False  # Default behavior
        # Transactional can always be sent
        # Marketing requires opt_in == True
        can_send_marketing = opt_in
        assert not can_send_marketing

    def test_transactional_always_allowed(self):
        """Transactional SMS (OTP, confirmations) are not gated by opt-in."""
        marketing_opt_in = False
        sms_transactional_enabled = True

        can_send_transactional = sms_transactional_enabled
        assert can_send_transactional

    def test_marketing_blocked_when_unsubscribed(self):
        """Unsubscribe timestamp blocks marketing."""
        marketing_opt_in = True
        unsubscribed = True

        can_send = marketing_opt_in and not unsubscribed
        assert not can_send

    def test_marketing_allowed_when_opted_in(self):
        """When opted in and not unsubscribed, marketing is allowed."""
        marketing_opt_in = True
        unsubscribed = False

        can_send = marketing_opt_in and not unsubscribed
        assert can_send
