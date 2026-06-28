"""Alembic migration and database integrity tests."""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg


def _test_db_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://fting@localhost:5432/hongshing_test",
    )


class TestAlembic:
    async def test_migrations_build_schema_with_zero_drift(self):
        """`alembic upgrade head` on an empty DB must build the full schema with
        no drift from the models (`alembic check`). This is the deploy gate: if a
        model changes without a matching migration, this fails."""
        backend_dir = Path(__file__).resolve().parent.parent
        base = _test_db_url().rsplit("/", 1)[0]            # postgresql+asyncpg://user@host:port
        admin_dsn = base.replace("+asyncpg", "") + "/postgres"
        tmp_db = f"hs_alembic_{uuid.uuid4().hex[:12]}"

        conn = await asyncpg.connect(admin_dsn)
        await conn.execute(f'CREATE DATABASE "{tmp_db}"')
        await conn.close()
        try:
            env = {**os.environ, "DATABASE_URL": f"{base}/{tmp_db}"}
            up = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=backend_dir, env=env, capture_output=True, text=True,
            )
            assert up.returncode == 0, f"alembic upgrade head failed:\n{up.stderr}"

            chk = subprocess.run(
                [sys.executable, "-m", "alembic", "check"],
                cwd=backend_dir, env=env, capture_output=True, text=True,
            )
            assert chk.returncode == 0, (
                "models drifted from migrations — run "
                "`alembic revision --autogenerate`:\n" + chk.stdout + chk.stderr
            )
        finally:
            conn = await asyncpg.connect(admin_dsn)
            await conn.execute(f'DROP DATABASE IF EXISTS "{tmp_db}" WITH (FORCE)')
            await conn.close()


class TestDatabaseSession:
    async def test_session_works(self, db_session):
        """Session can execute queries."""
        from sqlalchemy import text
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_all_models_exist(self, db_session):
        """All Phase 1 models are present in the database."""
        from sqlalchemy import inspect, text
        from app.database import Base

        expected_tables = {t.name for t in Base.metadata.sorted_tables}

        # Use async inspection via raw SQL
        result = await db_session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        actual_tables = {row[0] for row in result.fetchall()}

        missing = expected_tables - actual_tables
        assert not missing, f"Missing tables: {missing}"
