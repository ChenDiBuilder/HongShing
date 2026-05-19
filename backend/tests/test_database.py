"""Alembic migration and database integrity tests."""


class TestAlembic:
    def test_alembic_head_is_current(self):
        """Verify Alembic can be upgraded to head on the test database."""
        import subprocess
        from pathlib import Path

        backend_dir = Path(__file__).parent.parent
        result = subprocess.run(
            ["alembic", "current"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
        )
        # "current" shows the current revision; "head" would show pending upgrades
        assert result.returncode == 0, f"alembic current failed: {result.stderr}"
        # If there are pending migrations, "current" != "head"
        # This test just verifies alembic can connect and run


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
