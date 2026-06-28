"""Unit tests for fail-fast profile validation (PRD-12 S11 / SCRUM-79)."""

import copy

from app.cli.profile_validator import casl_warnings, validate_profile

VALID = {
    "identity": {"slug": "pho-99", "name": "Pho 99", "domain": "pho99.example.ca"},
    "branding": {"primary_color": "#123456", "secondary_color": "#ffffff"},
    "owner": {"email": "owner@pho99.example", "name": "Owner"},
    "locale": {"timezone": "America/Toronto"},
    "hours": {"open": "11:00", "close": "22:00"},
    "sms": {"origination_number": "+12494218942", "templates": {"otp": "code {code}"}},
    "rewards": [{"name": "10% off", "type": "percent", "value": 10}],
    "compliance": {"business_mailing_address": "1 Test St"},
}


def test_valid_profile_has_no_errors():
    assert validate_profile(copy.deepcopy(VALID)) == []


def test_missing_identity_name():
    p = copy.deepcopy(VALID)
    del p["identity"]["name"]
    assert "identity.name: required" in validate_profile(p)


def test_bad_slug():
    p = copy.deepcopy(VALID)
    p["identity"]["slug"] = "Pho 99!"
    assert any("identity.slug" in e for e in validate_profile(p))


def test_missing_domain():
    p = copy.deepcopy(VALID)
    p["identity"]["domain"] = ""
    assert "identity.domain: required" in validate_profile(p)


def test_bad_primary_color():
    p = copy.deepcopy(VALID)
    p["branding"]["primary_color"] = "#xyz"
    assert any("primary_color" in e for e in validate_profile(p))


def test_invalid_timezone():
    p = copy.deepcopy(VALID)
    p["locale"]["timezone"] = "Mars/Phobos"
    assert any("locale.timezone" in e for e in validate_profile(p))


def test_missing_owner_email():
    p = copy.deepcopy(VALID)
    p["owner"]["email"] = ""
    assert any("owner.email" in e for e in validate_profile(p))


def test_bad_origination_number():
    p = copy.deepcopy(VALID)
    p["sms"]["origination_number"] = "not-a-number"
    assert any("sms.origination_number" in e for e in validate_profile(p))


def test_sms_template_without_number():
    p = copy.deepcopy(VALID)
    p["sms"] = {"templates": {"otp": "code {code}"}}  # template set, no number
    assert any("sms.origination_number: required" in e for e in validate_profile(p))


def test_bad_reward_type():
    p = copy.deepcopy(VALID)
    p["rewards"][0]["type"] = "bogus"
    assert any("rewards[0].type" in e for e in validate_profile(p))


def test_non_numeric_reward_value():
    p = copy.deepcopy(VALID)
    p["rewards"][0]["value"] = "ten"
    assert any("rewards[0].value" in e for e in validate_profile(p))


def test_bad_hours_format():
    p = copy.deepcopy(VALID)
    p["hours"]["open"] = "9am"
    assert any("hours.open" in e for e in validate_profile(p))


def test_multiple_errors_accumulate():
    p = {"identity": {}, "branding": {}, "owner": {}}
    errs = validate_profile(p)
    assert len(errs) >= 4  # name, domain, slug, owner.email, primary_color...


def test_casl_warning_when_rewards_without_address():
    p = copy.deepcopy(VALID)
    p["compliance"]["business_mailing_address"] = ""
    warnings = casl_warnings(p)
    assert warnings and "business_mailing_address" in warnings[0]


def test_no_casl_warning_when_address_present():
    assert casl_warnings(copy.deepcopy(VALID)) == []
