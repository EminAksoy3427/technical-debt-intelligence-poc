from logging.config import fileConfig

import app.infrastructure.database.action_approval_models  # noqa: F401
import app.infrastructure.database.action_policy_models  # noqa: F401
import app.infrastructure.database.action_proposal_models  # noqa: F401
import app.infrastructure.database.agent_audit_models  # noqa: F401
import app.infrastructure.database.candidate_models  # noqa: F401
import app.infrastructure.database.enterprise_estate_models  # noqa: F401
import app.infrastructure.database.human_decision_models  # noqa: F401
import app.infrastructure.database.signal_models  # noqa: F401
import app.infrastructure.database.technical_debt_models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.engine import create_database_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    database_engine = create_database_engine(settings)
    try:
        context.configure(
            url=database_engine.url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()
    finally:
        database_engine.dispose()


def run_migrations_online() -> None:
    """Run migrations using the configured database connection."""
    database_engine = create_database_engine(settings)
    try:
        with database_engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        database_engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
