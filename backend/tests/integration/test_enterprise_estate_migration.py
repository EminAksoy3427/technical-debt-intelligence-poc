from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from app.core.config import Settings
from app.infrastructure.database.engine import create_database_engine

EXPECTED_TABLES = {
    "enterprise_assets",
    "teams",
    "asset_ownerships",
    "asset_relationships",
    "incidents",
    "signals",
    "evidence",
    "candidates",
    "candidate_signals",
    "agent_runs",
    "tool_executions",
    "policy_decisions",
    "human_decisions",
    "technical_debts",
}


@pytest.mark.integration
def test_mssql_can_migrate_enterprise_estate_schema_to_head() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")

    engine = create_database_engine(app_settings)
    try:
        table_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert EXPECTED_TABLES <= table_names
