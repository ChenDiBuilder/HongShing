"""Unit tests for profile-driven SMS templating (PRD-12 S3 / SCRUM-60)."""

from app.services.sms_service import DEFAULT_OTP_TEMPLATE, render_otp_message


def test_otp_default_when_template_none():
    msg = render_otp_message(None, "Pho 99", "123456")
    assert msg == "Your Pho 99 verification code is 123456. It expires in 5 minutes."
    assert msg == DEFAULT_OTP_TEMPLATE.format(restaurant="Pho 99", code="123456")


def test_otp_uses_configured_template():
    msg = render_otp_message("{restaurant}: code {code}", "Pho 99", "123456")
    assert msg == "Pho 99: code 123456"


def test_otp_malformed_template_falls_back_to_default():
    # Unknown placeholder would raise KeyError on .format — must fall back, never 500.
    msg = render_otp_message("Your code is {otp} for {restaurant}", "Pho 99", "123456")
    assert msg == DEFAULT_OTP_TEMPLATE.format(restaurant="Pho 99", code="123456")


def test_otp_stray_brace_falls_back():
    # A lone '{' is a ValueError in str.format — must also fall back.
    msg = render_otp_message("code {code} {", "Pho 99", "123456")
    assert msg == DEFAULT_OTP_TEMPLATE.format(restaurant="Pho 99", code="123456")
