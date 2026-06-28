"""Fail-fast Restaurant Profile validation (PRD-12 S11 / SCRUM-79).

A pure, stdlib-only validator so it runs inside the prod container with no extra
dependency (jsonschema is not installed there). `validate_profile` returns a list
of human-readable error strings (empty == valid); the seeder rejects a malformed
profile BEFORE opening a DB session, and the provisioner runs a lighter pre-flight
before any cloud resource is created — so a bad profile never produces a
half-branded live box.
"""

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")
TIME_RE = re.compile(r"^[0-2][0-9]:[0-5][0-9]$")
PHONE_RE = re.compile(r"^\+[0-9]{8,15}$")
REWARD_TYPES = {"percent", "fixed", "freebie"}


def validate_profile(profile: dict) -> list[str]:
    """Return a list of fatal validation errors for a parsed profile dict."""
    if not isinstance(profile, dict):
        return ["profile: must be a YAML mapping"]

    errors: list[str] = []

    ident = profile.get("identity") or {}
    if not isinstance(ident, dict):
        errors.append("identity: must be a mapping")
        ident = {}
    slug = str(ident.get("slug") or "").strip()
    if not slug:
        errors.append("identity.slug: required")
    elif not SLUG_RE.match(slug):
        errors.append("identity.slug: must match ^[a-z0-9-]+$ (lowercase, digits, hyphens)")
    if not str(ident.get("name") or "").strip():
        errors.append("identity.name: required")
    if not str(ident.get("domain") or "").strip():
        errors.append("identity.domain: required")

    owner = profile.get("owner") or {}
    email = str(owner.get("email") or "").strip() if isinstance(owner, dict) else ""
    if not email or "@" not in email:
        errors.append("owner.email: required (a valid email — the admin login is keyed on it)")

    branding = profile.get("branding") or {}
    if isinstance(branding, dict):
        pc = branding.get("primary_color")
        if not pc:
            errors.append("branding.primary_color: required")
        elif not HEX_RE.match(str(pc)):
            errors.append("branding.primary_color: must be a #RRGGBB hex colour")
        sc = branding.get("secondary_color")
        if sc and not HEX_RE.match(str(sc)):
            errors.append("branding.secondary_color: must be a #RRGGBB hex colour")

    locale = profile.get("locale") or {}
    tz = (locale.get("timezone") if isinstance(locale, dict) else None) or "America/Toronto"
    try:
        ZoneInfo(str(tz))
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        errors.append(f"locale.timezone: '{tz}' is not a valid IANA timezone")

    hours = profile.get("hours") or {}
    if isinstance(hours, dict):
        for key in ("open", "close"):
            v = hours.get(key)
            if v is not None and not TIME_RE.match(str(v)):
                errors.append(f"hours.{key}: must be HH:MM (24-hour), got '{v}'")

    sms = profile.get("sms") if isinstance(profile.get("sms"), dict) else {}
    templates = sms.get("templates") if isinstance(sms.get("templates"), dict) else {}
    origination = str(sms.get("origination_number") or "").strip()
    uses_sms = bool(templates.get("otp") or templates.get("reward") or origination)
    if uses_sms:
        if not origination:
            errors.append("sms.origination_number: required when sms.templates are configured")
        elif not PHONE_RE.match(origination):
            errors.append("sms.origination_number: must be E.164 (e.g. +12494218942)")

    rewards = profile.get("rewards") or []
    if isinstance(rewards, list):
        for i, r in enumerate(rewards):
            if not isinstance(r, dict):
                errors.append(f"rewards[{i}]: must be a mapping")
                continue
            if not str(r.get("name") or "").strip():
                errors.append(f"rewards[{i}].name: required")
            rtype = r.get("type", "fixed")
            if rtype not in REWARD_TYPES:
                errors.append(f"rewards[{i}].type: must be one of percent|fixed|freebie")
            if "value" in r:
                try:
                    int(r["value"])
                except (TypeError, ValueError):
                    errors.append(f"rewards[{i}].value: must be numeric")

    menu = profile.get("menu")
    if menu is not None:
        if not isinstance(menu, list):
            errors.append("menu: must be a list of categories")
        else:
            for i, cat in enumerate(menu):
                if not isinstance(cat, dict):
                    errors.append(f"menu[{i}]: must be a mapping")
                    continue
                if not str(cat.get("name") or "").strip():
                    errors.append(f"menu[{i}].name: required")
                items = cat.get("items") or []
                if not isinstance(items, list):
                    errors.append(f"menu[{i}].items: must be a list")
                    continue
                for j, it in enumerate(items):
                    if not isinstance(it, dict):
                        errors.append(f"menu[{i}].items[{j}]: must be a mapping")
                        continue
                    if not str(it.get("name") or "").strip():
                        errors.append(f"menu[{i}].items[{j}].name: required")
                    if "price" not in it:
                        errors.append(f"menu[{i}].items[{j}].price: required (dollars)")
                    else:
                        try:
                            float(it["price"])
                        except (TypeError, ValueError):
                            errors.append(f"menu[{i}].items[{j}].price: must be numeric")

    return errors


def casl_warnings(profile: dict) -> list[str]:
    """Non-fatal advisories (printed, never blocking). Reward marketing SMS is
    skipped without a CASL mailing address — matches the SCRUM-64 decision."""
    if not isinstance(profile, dict):
        return []
    warnings: list[str] = []
    rewards = profile.get("rewards") or []
    comp = profile.get("compliance") or {}
    addr = str(comp.get("business_mailing_address") or "").strip() if isinstance(comp, dict) else ""
    if rewards and not addr:
        warnings.append(
            "compliance.business_mailing_address is empty — reward marketing SMS will be "
            "skipped (CASL requires a mailing address in the footer)."
        )
    return warnings
