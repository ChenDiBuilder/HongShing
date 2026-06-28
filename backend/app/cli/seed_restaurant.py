"""Seed a restaurant's config from a Restaurant Profile (PRD-11 / SCRUM-50).

Reads a profile YAML and populates restaurant_settings (single-row config),
reward_templates, qr_campaigns, and the owner user. Idempotent: re-running
updates settings and skips rows that already exist (by name / source_code /
email), so it is safe to re-run after editing a profile.

The profile path is resolved at runtime, so this runs in the container via:
    docker exec <backend> python -m app.cli seed-restaurant --profile /tmp/<slug>.yaml
"""

import json
import secrets

import click
import yaml
from sqlalchemy import select

from app.database import async_session
from app.models import QRCampaign, RestaurantSettings, RewardTemplate, User
from app.services.auth_service import hash_password


def _code_prefix(name: str, slug: str) -> str:
    """Short reward-code prefix from the restaurant name initials, else the slug."""
    initials = "".join(w[0] for w in name.split() if w)
    return (initials or slug)[:10].upper()


def _maybe_validate(profile: dict, schema_path) -> None:
    """Best-effort schema validation — skipped if jsonschema/schema isn't available."""
    try:
        import json

        import jsonschema
    except ImportError:
        return
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except OSError:
        return
    jsonschema.validate(profile, schema)


async def seed_restaurant(
    profile_path: str, owner_password: str | None = None, session_factory=None
) -> None:
    from pathlib import Path

    factory = session_factory or async_session

    path = Path(profile_path)
    with open(path) as f:
        profile = yaml.safe_load(f)

    _maybe_validate(profile, path.parent / "restaurant.schema.json")

    ident = profile["identity"]
    branding = profile.get("branding", {}) or {}
    ordering = profile.get("ordering", {}) or {}
    rewards = profile.get("rewards", []) or []
    campaigns = profile.get("campaigns", []) or []
    locale = profile.get("locale", {}) or {}
    compliance = profile.get("compliance", {}) or {}
    location = profile.get("location", {}) or {}
    pricing = profile.get("pricing", {}) or {}
    owner = profile.get("owner", {}) or {}

    raw_domain = (ident.get("domain") or "").replace("https://", "").replace("http://", "").rstrip("/")
    public_domain = f"https://{raw_domain}" if raw_domain else None

    logo = branding.get("logo")
    # Only store a real served URL; relative asset paths are wired by the branding
    # pipeline at provision time, so don't seed a broken image src.
    logo_url = logo if (logo and logo.startswith("http")) else None

    hours_display = location.get("hours_display") or None
    hours_json = json.dumps(hours_display) if hours_display else None

    temp_pw = None
    async with factory() as session:
        # 1) Reward templates (idempotent by name).
        reward_ids: dict[str, str] = {}
        for r in rewards:
            existing = (
                await session.execute(select(RewardTemplate).where(RewardTemplate.name == r["name"]))
            ).scalar_one_or_none()
            if existing:
                reward_ids[r["name"]] = existing.id
                click.echo(f"  reward exists: {r['name']}")
                continue
            rt = RewardTemplate(
                name=r["name"],
                code_prefix=_code_prefix(ident["name"], ident["slug"]),
                reward_type=r.get("type", "fixed"),
                reward_value=int(r.get("value", 0)),
                valid_days=int(r.get("valid_days", 30)),
            )
            session.add(rt)
            await session.flush()
            reward_ids[r["name"]] = rt.id
            click.echo(f"  reward created: {r['name']}")
        default_reward_id = reward_ids.get(rewards[0]["name"]) if rewards else None

        # 2) Restaurant settings — single-row config, upsert.
        fields = dict(
            restaurant_name=ident["name"],
            logo_url=logo_url,
            primary_color=branding.get("primary_color", "#C41E3A"),
            secondary_color=branding.get("secondary_color"),
            external_ordering_url=ordering.get("external_url") or None,
            external_ordering_provider=ordering.get("provider") or None,
            allow_order_without_signup=bool(ordering.get("allow_without_signup", True)),
            default_reward_template_id=default_reward_id,
            timezone=locale.get("timezone", "America/Toronto"),
            privacy_contact_email=compliance.get("privacy_contact_email") or None,
            support_phone=compliance.get("support_phone") or None,
            public_domain=public_domain,
            address=location.get("address") or None,
            contact_phone=location.get("phone") or None,
            hours_json=hours_json,
            pickup_estimate=location.get("pickup_estimate") or None,
            tax_rate=pricing.get("tax_rate"),
            currency_symbol=pricing.get("currency_symbol") or None,
        )
        settings_row = (await session.execute(select(RestaurantSettings))).scalars().first()
        if settings_row:
            for k, v in fields.items():
                setattr(settings_row, k, v)
            click.echo("  settings updated")
        else:
            session.add(RestaurantSettings(**fields))
            click.echo("  settings created")

        # 3) QR campaigns (idempotent by source_code).
        for c in campaigns:
            src = c["source"]
            existing = (
                await session.execute(select(QRCampaign).where(QRCampaign.source_code == src))
            ).scalar_one_or_none()
            if existing:
                click.echo(f"  campaign exists: {src}")
                continue
            session.add(
                QRCampaign(
                    name=src.replace("_", " ").title(),
                    source_code=src,
                    reward_template_id=default_reward_id,
                    active=True,
                )
            )
            click.echo(f"  campaign created: {src}")

        # 4) Owner user (idempotent by email; temp password forces a reset on first login).
        email = owner.get("email")
        if email:
            existing_owner = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing_owner:
                click.echo(f"  owner exists: {email}")
            else:
                temp_pw = owner_password or secrets.token_urlsafe(12)
                session.add(
                    User(
                        email=email,
                        name=owner.get("name", "Owner"),
                        password_hash=hash_password(temp_pw),
                        password_changed_at=None,
                        role="owner",
                    )
                )
                click.echo(f"  owner created: {email}")

        await session.commit()

    click.echo(f"Seeded restaurant '{ident['slug']}' from {profile_path}")
    if temp_pw:
        click.echo(f"  OWNER TEMP PASSWORD: {temp_pw}  (change on first login)")
