from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from app.core.config import Settings, settings


class DatabaseConfigurationError(RuntimeError):
    """Raised when database infrastructure is used without valid configuration."""


def _database_url(app_settings: Settings) -> URL:
    if app_settings.database_url is None:
        raise DatabaseConfigurationError(
            "Database configuration is missing; set DATABASE_URL."
        )

    try:
        database_url = make_url(app_settings.database_url.get_secret_value())
    except ArgumentError:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not a valid SQLAlchemy URL."
        ) from None

    if database_url.drivername != "mssql+pyodbc":
        raise DatabaseConfigurationError(
            "DATABASE_URL must use the mssql+pyodbc SQLAlchemy dialect."
        )

    return database_url


def create_database_engine(app_settings: Settings = settings) -> Engine:
    """Construct the synchronous MSSQL SQLAlchemy engine."""
    return create_engine(
        _database_url(app_settings),
        connect_args={
            "timeout": app_settings.database_connection_timeout_seconds,
        },
        pool_pre_ping=True,
    )


def check_database_connectivity(engine: Engine) -> None:
    """Verify database connectivity with the smallest useful query."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    if result != 1:
        raise RuntimeError("Database connectivity check returned an unexpected value.")
