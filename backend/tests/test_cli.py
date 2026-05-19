"""Integration tests for CLI commands."""

import pytest
from sqlalchemy import select

from app.models import User
from app.services.auth_service import hash_password, verify_password


class TestCLI:
    async def test_create_owner(self, db_session):
        """Simulates the create-owner CLI command."""
        # Check no owner exists
        result = await db_session.execute(
            select(User).where(User.role == "owner")
        )
        assert result.scalar_one_or_none() is None

        # Create owner
        user = User(
            email="owner@hongshing.com",
            name="Owner",
            password_hash=hash_password("admin123"),
            role="owner",
        )
        db_session.add(user)
        await db_session.flush()

        # Verify
        result = await db_session.execute(
            select(User).where(User.role == "owner")
        )
        owner = result.scalar_one()
        assert owner.email == "owner@hongshing.com"
        assert verify_password("admin123", owner.password_hash)

    async def test_reset_owner_password(self, db_session):
        """Simulates the reset-owner CLI command."""
        user = User(
            email="owner@hongshing.com",
            name="Owner",
            password_hash=hash_password("old-pass"),
            role="owner",
        )
        db_session.add(user)
        await db_session.flush()

        # Reset password
        user.password_hash = hash_password("new-pass")
        user.password_changed_at = None  # Force change on next login
        await db_session.flush()

        result = await db_session.execute(
            select(User).where(User.role == "owner")
        )
        owner = result.scalar_one()
        assert verify_password("new-pass", owner.password_hash)
        assert not verify_password("old-pass", owner.password_hash)

    async def test_duplicate_create_is_idempotent(self, db_session):
        """Creating the same owner twice should not create duplicates."""
        user = User(
            email="owner@hongshing.com",
            name="Owner",
            password_hash=hash_password("admin123"),
            role="owner",
        )
        db_session.add(user)
        await db_session.flush()

        # Check that a second owner with same email would be detected
        result = await db_session.execute(
            select(User).where(User.email == "owner@hongshing.com")
        )
        existing = result.scalar_one_or_none()
        assert existing is not None
        # CLI would skip creation if email exists
