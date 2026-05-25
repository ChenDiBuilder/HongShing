import asyncio

import click
from sqlalchemy import select

from app.config import get_settings

settings = get_settings()
from app.database import async_session
from app.models import User
from app.services.auth_service import hash_password


@click.group()
def cli():
    """HongShing management CLI."""
    pass


@cli.command()
@click.option("--email", required=True)
@click.option("--password", required=True)
@click.option("--name", default="Owner")
def create_owner(email: str, password: str, name: str):
    """Create the initial owner account."""
    asyncio.run(_create_owner(email, password, name))


async def _create_owner(email: str, password: str, name: str):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            click.echo(f"Owner {email} already exists (id={existing.id})")
            return

        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            password_changed_at=None,
            role="owner",
        )
        session.add(user)
        await session.commit()
        click.echo(f"Owner created: {email} (id={user.id})")


@cli.command()
@click.option("--email", required=True)
def reset_owner(email: str):
    """Reset owner password. Prompts for new password."""
    new_password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    asyncio.run(_reset_owner(email, new_password))


async def _reset_owner(email: str, new_password: str):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == email, User.role == "owner")
        )
        user = result.scalar_one_or_none()
        if not user:
            click.echo(f"No owner found with email {email}")
            return

        user.password_hash = hash_password(new_password)
        user.password_changed_at = None  # Force password change on next login
        await session.commit()
        click.echo(f"Password reset for {email}")


@cli.command()
@click.option("--force", is_flag=True, help="Force re-seed (clears existing menu)")
def seed_menu(force: bool = False):
    """Seed the database with the HongShing menu."""
    from app.cli.seed_menu import seed_menu as _seed
    asyncio.run(_seed(force=force))


@cli.command()
@click.option("--keep-admin/--no-keep-admin", default=True)
@click.confirmation_option(prompt="This will delete all test data (customers, orders, reservations, devices). Continue?")
def reset_demo(keep_admin: bool):
    """Reset demo data — delete test customers, orders, reservations, and devices."""
    asyncio.run(_reset_demo(keep_admin))


async def _reset_demo(keep_admin: bool):
    from sqlalchemy import delete, text

    async with async_session() as session:
        tables = [
            "order_status_events",
            "order_items",
            "orders",
            "reservations",
            "signup_events",
            "qr_scan_events",
            "rewards",
            "external_order_redirects",
            "user_notification_preferences",
            "refresh_tokens",
            "otp_codes",
            "otp_rate_limits",
            "test_sms_messages",
            "devices",
        ]
        for table in tables:
            await session.execute(text(f"DELETE FROM {table}"))
            click.echo(f"  Cleared {table}")

        if keep_admin:
            await session.execute(
                text("DELETE FROM users WHERE role = 'customer'")
            )
            click.echo("  Deleted customer users (kept admin accounts)")
        else:
            await session.execute(text("DELETE FROM users"))
            click.echo("  Deleted ALL users")

        # Clear reservation slots
        await session.execute(text("DELETE FROM reservation_slots"))
        click.echo("  Cleared reservation_slots")

        await session.commit()
        click.echo("Demo data reset complete.")


if __name__ == "__main__":
    cli()
