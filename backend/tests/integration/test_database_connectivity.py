import pytest

from app.core.config import Settings
from app.infrastructure.database.engine import (
    check_database_connectivity,
    create_database_engine,
)


@pytest.mark.integration
def test_configured_mssql_database_accepts_select_one() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    engine = create_database_engine(app_settings)
    try:
        check_database_connectivity(engine)
    finally:
        engine.dispose()
