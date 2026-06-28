from app.services.reward_service import (
    generate_reward_code,
    calculate_discount,
)


class TestRewardCodeGeneration:
    def test_code_format(self):
        code = generate_reward_code()
        # Format: HS-XXXXXX where X is Crockford Base32 (no O,0,I,1)
        assert code.startswith("HS-")
        assert len(code) == 9  # "HS-" + 6 chars
        segment = code[3:]
        assert len(segment) == 6
        for ch in segment:
            assert ch not in "O0I1"
            assert ch in "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

    def test_codes_are_unique(self):
        codes = {generate_reward_code() for _ in range(100)}
        assert len(codes) == 100

    def test_code_characters_are_uppercase(self):
        code = generate_reward_code()
        segment = code[3:]
        assert segment == segment.upper()

    def test_no_ambiguous_characters(self):
        for _ in range(1000):
            code = generate_reward_code()
            segment = code[3:]
            assert "O" not in segment
            assert "0" not in segment
            assert "I" not in segment
            assert "1" not in segment


class TestDiscountCalculation:
    def test_percentage_discount(self):
        # 20% off 1000 cents ($10.00) = 200 cents
        assert calculate_discount("percentage", 20, 1000) == 200

    def test_percentage_rounds_down(self):
        # 15% off 999 cents = 149 (floor, not 150)
        assert calculate_discount("percentage", 15, 999) == 149

    def test_fixed_discount_within_total(self):
        # $5 off $10
        assert calculate_discount("fixed", 500, 1000) == 500

    def test_fixed_discount_capped_at_subtotal(self):
        # $15 off $10 → capped at $10
        assert calculate_discount("fixed", 1500, 1000) == 1000

    def test_zero_percent(self):
        assert calculate_discount("percentage", 0, 1000) == 0

    def test_zero_subtotal(self):
        assert calculate_discount("percentage", 50, 0) == 0


class TestRewardSms:
    """CASL reward-SMS gate + render (PRD-12 S7 / SCRUM-64)."""

    def test_gate_sends_only_when_all_present(self):
        from app.services.reward_service import should_send_reward_sms

        assert should_send_reward_sms(True, "1 St", "tmpl", "+1") is True
        assert should_send_reward_sms(False, "1 St", "tmpl", "+1") is False  # no consent
        assert should_send_reward_sms(True, "", "tmpl", "+1") is False       # no address
        assert should_send_reward_sms(True, "1 St", None, "+1") is False     # no template
        assert should_send_reward_sms(True, "1 St", "tmpl", None) is False   # no phone

    def test_render_includes_code_and_casl_footer(self):
        from app.services.reward_service import render_reward_sms

        msg = render_reward_sms(
            "{restaurant}: reward {reward_code} — {ordering_url}",
            "Pho 99", "PH-ABC123", "https://pho99.ca/order", "1 King St, Toronto",
        )
        assert "PH-ABC123" in msg
        assert "1 King St, Toronto" in msg          # CASL mailing address in footer
        assert "STOP" in msg                         # opt-out hint

    def test_render_falls_back_on_bad_template(self):
        from app.services.reward_service import DEFAULT_REWARD_SMS_TEMPLATE, render_reward_sms

        msg = render_reward_sms("{unknown}", "Pho 99", "PH-1", "u", "addr")
        assert "PH-1" in msg
        assert DEFAULT_REWARD_SMS_TEMPLATE.split("{")[0] in msg
