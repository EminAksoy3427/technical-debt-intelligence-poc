from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.infrastructure.database.engine import (
    DatabaseConfigurationError,
    check_database_connectivity,
    create_database_engine,
)


def test_database_configuration_can_be_absent() -> None:
    app_settings = Settings(_env_file=None, database_url=None)

    assert app_settings.database_url is None


def test_engine_creation_fails_clearly_without_database_url() -> None:
    app_settings = Settings(_env_file=None, database_url=None)

    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL"):
        create_database_engine(app_settings)


def test_engine_uses_mssql_pyodbc_without_exposing_password() -> None:
    password = "unit-test-secret"
    app_settings = Settings(
        _env_file=None,
        database_url=SecretStr(
            f"mssql+pyodbc://test-user:{password}@db.example/test-db"
            "?driver=ODBC+Driver+17+for+SQL+Server"
        ),
        database_connection_timeout_seconds=9,
    )

    engine = create_database_engine(app_settings)
    try:
        assert engine.url.drivername == "mssql+pyodbc"
        assert engine.pool._pre_ping is True
        assert password not in repr(app_settings)
        assert password not in str(engine.url)
        assert password not in repr(engine)
    finally:
        engine.dispose()


def test_connectivity_check_executes_select_one() -> None:
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = 1

    check_database_connectivity(engine)

    statement = connection.execute.call_args.args[0]
    assert str(statement) == "SELECT 1"
