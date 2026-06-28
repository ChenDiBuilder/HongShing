"""Tests for the profile-driven seeder (SCRUM-50) — requires a test database."""

import json
import os

import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cli.seed_restaurant import seed_restaurant
from app.models import Base, QRCampaign, RestaurantSettings, RewardTemplate, User

PROFILE = """\
identity: {slug: testaurant, name: "Test Bistro", domain: testaurant.demo.bridgewayinnovations.ca}
branding: {primary_color: "#123456", logo: "assets/testaurant/logo.png"}
ordering: {external_url: "https://order.example.com/test", provider: toast, allow_without_signup: true}
rewards: [{name: "10% off your order", type: percent, value: 10}]
campaigns: [{source: table_tent}, {source: counter}]
sms: {origination_number: "+12494218942", region: us-east-2}
locale: {timezone: "America/Toronto"}
location:
  address: "1 Test St, Toronto, ON"
  phone: "+14165550123"
  pickup_estimate: "15–25 minutes"
  hours_display: {Mon: "11:00 AM – 9:00 PM", Tue: "Closed"}
pricing: {tax_rate: 0.13, currency_symbol: "$"}
hours: {open: "11:00", close: "22:00"}
owner: {email: "owner@test.example", name: "Test Owner"}
"""


def _test_db_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL", "postgresql+asyncpg://fting@localhost:5432/hongshing_test"
    )


@pytest_asyncio.fixture
async def factory():
    engine = create_async_engine(_test_db_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


async def _counts(session_factory):
    async with session_factory() as s:
        return {
            "settings": await s.scalar(select(func.count(RestaurantSettings.id))),
            "rewards": await s.scalar(select(func.count(RewardTemplate.id))),
            "campaigns": await s.scalar(select(func.count(QRCampaign.id))),
            "owners": await s.scalar(select(func.count(User.id)).where(User.role == "owner")),
        }


async def test_seed_populates_all_layers(factory, tmp_path):
    profile = tmp_path / "testaurant.yaml"
    profile.write_text(PROFILE)

    await seed_restaurant(str(profile), owner_password="pw123456", session_factory=factory)

    assert await _counts(factory) == {"settings": 1, "rewards": 1, "campaigns": 2, "owners": 1}

    async with factory() as s:
        settings = (await s.execute(select(RestaurantSettings))).scalar_one()
        assert settings.restaurant_name == "Test Bistro"
        assert settings.primary_color == "#123456"
        assert settings.external_ordering_url == "https://order.example.com/test"
        assert settings.external_ordering_provider == "toast"
        assert settings.logo_url is None  # relative asset path -> not seeded as a URL
        assert settings.default_reward_template_id is not None
        # PRD-12 S8 — customer-facing display fields from location/pricing
        assert settings.address == "1 Test St, Toronto, ON"
        assert settings.contact_phone == "+14165550123"
        assert settings.pickup_estimate == "15–25 minutes"
        assert json.loads(settings.hours_json) == {"Mon": "11:00 AM – 9:00 PM", "Tue": "Closed"}
        assert settings.tax_rate == 0.13
        assert settings.currency_symbol == "$"

        reward = (await s.execute(select(RewardTemplate))).scalar_one()
        assert reward.name == "10% off your order"
        assert reward.reward_type == "percent"
        assert reward.reward_value == 10
        assert reward.code_prefix == "TB"  # initials of "Test Bistro"

        sources = {c.source_code for c in (await s.execute(select(QRCampaign))).scalars()}
        assert sources == {"table_tent", "counter"}

        owner = (await s.execute(select(User).where(User.role == "owner"))).scalar_one()
        assert owner.email == "owner@test.example"
        assert owner.password_changed_at is None  # forces reset on first login


async def test_seed_is_idempotent(factory, tmp_path):
    profile = tmp_path / "testaurant.yaml"
    profile.write_text(PROFILE)

    await seed_restaurant(str(profile), owner_password="pw123456", session_factory=factory)
    await seed_restaurant(str(profile), owner_password="pw123456", session_factory=factory)

    # Re-running must not duplicate any rows.
    assert await _counts(factory) == {"settings": 1, "rewards": 1, "campaigns": 2, "owners": 1}
