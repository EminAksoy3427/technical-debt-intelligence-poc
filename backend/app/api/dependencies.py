from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.infrastructure.database.engine import create_database_engine


def get_database_session() -> Iterator[Session]:
    """Provide a caller-scoped read session without committing."""
    engine = create_database_engine()
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()
