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
def seed_menu():
    """Seed the database with the HongShing menu."""
    from app.cli.seed_menu import seed_menu as _seed
    asyncio.run(_seed())


if __name__ == "__main__":
    cli()
