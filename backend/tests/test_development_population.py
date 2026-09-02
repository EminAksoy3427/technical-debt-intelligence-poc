import ast
import importlib
import inspect
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.config import Settings
from app.development_population import (
    DevelopmentPopulationDisabledError,
    DevelopmentPopulationError,
    DevelopmentPopulationResult,
    main,
    populate_development_candidates,
    run_development_population,
)
from app.domain.candidates import Candidate
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_models import IncidentModel
from app.infrastructure.database.signal_models import SignalModel
from app.infrastructure.semgrep import SemgrepFinding
from app.semgrep_ingestion import normalize_semgrep_finding
from app.signal_ingestion import NormalizedSignal

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
CONTROLLED_REPOSITORY_ROOT = PROJECT_ROOT / "synthetic_repositories"
RULES_PATH = BACKEND_ROOT / "semgrep" / "rules.yml"
DETECTED_AT = datetime(2026, 8, 29, 12, 30, tzinfo=UTC)
CONTROLLED_REPOSITORY_ASSET_KEYS = (
    "repo-asteria-editor",
    "repo-borealis-renderer",
    "repo-orbit-catalog",
)
POPULATION_MODULE_NAME = "app.development_population"


CONTROLLED_SEMGREP_FINDINGS = {
    "repo-asteria-editor": SemgrepFinding(
        rule_id="tdi.python.hardcoded-endpoint",
        relative_path="catalog_client.py",
        start_line=4,
        start_column=20,
        end_line=4,
        end_column=64,
        message="A network endpoint is hard-coded in Python source.",
        severity="WARNING",
    ),
    "repo-borealis-renderer": SemgrepFinding(
        rule_id="tdi.python.missing-timeout",
        relative_path="renderer_client.py",
        start_line=5,
        start_column=10,
        end_line=5,
        end_column=52,
        message="A urllib request is made without an explicit timeout.",
        severity="WARNING",
    ),
    "repo-orbit-catalog": SemgrepFinding(
        rule_id="tdi.python.process-local-state",
        relative_path="catalog_cache.py",
        start_line=1,
        start_column=1,
        end_line=1,
        end_column=36,
        message="Mutable dictionary state is stored at Python module scope.",
        severity="WARNING",
    ),
}


def _normalize_controlled_semgrep(asset_key: str) -> NormalizedSignal:
    return normalize_semgrep_finding(
        CONTROLLED_SEMGREP_FINDINGS[asset_key],
        repository_asset_key=asset_key,
        detected_at=DETECTED_AT,
    )


def _enabled_settings() -> Settings:
    return Settings(_env_file=None, allow_development_data_population=True)


def _disabled_settings() -> Settings:
    return Settings(_env_file=None, allow_development_data_population=False)


def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
            names.update(
                (
                    node.module
                    if alias.name == "*"
                    else f"{node.module}.{alias.name}"
                )
                for alias in node.names
            )
    return names


@pytest.fixture
def cached_semgrep_scan(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    scanned_asset_keys: list[str] = []

    def fake_scan(
        repository_path: Path,
        repository_asset_key: str,
        detected_at: datetime,
        rules_path: Path,
        **kwargs: object,
    ) -> tuple[NormalizedSignal, ...]:
        scanned_asset_keys.append(repository_asset_key)
        assert repository_path == CONTROLLED_REPOSITORY_ROOT / repository_asset_key
        assert rules_path == RULES_PATH
        assert detected_at == DETECTED_AT
        return (_normalize_controlled_semgrep(repository_asset_key),)

    monkeypatch.setattr(
        "app.development_population.scan_and_normalize_semgrep_repository",
        fake_scan,
    )
    return scanned_asset_keys


@pytest.fixture
def sqlite_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    revisions = list(scripts.walk_revisions(base="base", head="heads"))

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    def restore_incident_timestamps(target: IncidentModel, _context: object) -> None:
        if target.started_at is not None and target.started_at.tzinfo is None:
            set_committed_value(
                target,
                "started_at",
                target.started_at.replace(tzinfo=UTC),
            )
        if target.resolved_at is not None and target.resolved_at.tzinfo is None:
            set_committed_value(
                target,
                "resolved_at",
                target.resolved_at.replace(tzinfo=UTC),
            )

    event.listen(IncidentModel, "load", restore_incident_timestamps)
    try:
        yield engine
    finally:
        event.remove(IncidentModel, "load", restore_incident_timestamps)
        engine.dispose()


def test_development_guard_defaults_to_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOW_DEVELOPMENT_DATA_POPULATION", raising=False)

    assert Settings(_env_file=None).allow_development_data_population is False


def test_population_refuses_when_guard_is_disabled() -> None:
    with pytest.raises(DevelopmentPopulationDisabledError, match="disabled"):
        populate_development_candidates(
            MagicMock(),
            app_settings=_disabled_settings(),
        )


def test_disabled_guard_does_not_mutate_or_orchestrate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.development_population.seed_enterprise_estate",
        lambda session: (_ for _ in ()).throw(AssertionError("seed called")),
    )
    monkeypatch.setattr(
        "app.development_population.create_database_engine",
        lambda app_settings: (_ for _ in ()).throw(AssertionError("engine created")),
    )
    monkeypatch.setattr(
        "app.development_population.populate_development_candidates",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("orchestration called")
        ),
    )

    with pytest.raises(DevelopmentPopulationDisabledError, match="disabled"):
        populate_development_candidates(
            MagicMock(),
            app_settings=_disabled_settings(),
        )
    with pytest.raises(DevelopmentPopulationDisabledError, match="disabled"):
        run_development_population(_disabled_settings())
    with pytest.raises(DevelopmentPopulationDisabledError, match="disabled"):
        monkeypatch.setattr(
            "app.development_population.settings",
            _disabled_settings(),
        )
        main()


def test_runtime_imports_semgrep_and_incidents_only() -> None:
    source = inspect.getsource(importlib.import_module(POPULATION_MODULE_NAME))
    imported = _imported_module_names(source)

    assert "app.semgrep_ingestion" in imported
    assert "app.incident_ingestion" in imported
    assert "app.infrastructure.database.incident_loading" in imported
    assert "app.candidate_correlation" in imported
    assert "app.infrastructure.database.signal_persistence" in imported
    assert "app.infrastructure.database.candidate_persistence" in imported
    assert "app.infrastructure.database.enterprise_estate_seed" in imported
    assert "app.git_history_ingestion" not in imported
    assert "app.infrastructure.git_history" not in imported
    assert "app.dependency_lifecycle_ingestion" not in imported
    assert "app.infrastructure.dependency_lifecycle" not in imported
    assert "app.infrastructure.database.dependency_lifecycle_loading" not in imported


def test_runtime_does_not_consume_evaluation_or_test_fixtures() -> None:
    source = inspect.getsource(importlib.import_module(POPULATION_MODULE_NAME))
    imported = _imported_module_names(source)

    assert not any("evaluation" in name for name in imported)
    assert not any(name.startswith("tests") or ".tests" in name for name in imported)
    assert "correlation_cases.json" not in source
    assert "ground_truth" not in source
    assert "materialize_controlled_git_repository" not in source
    assert "pytest" not in imported
    assert "alembic" not in imported


def test_controlled_semgrep_scan_yields_three_normalized_signals() -> None:
    signals = tuple(
        _normalize_controlled_semgrep(asset_key)
        for asset_key in CONTROLLED_REPOSITORY_ASSET_KEYS
    )

    assert len(signals) == 3
    assert {item.signal.signal_type for item in signals} == {
        "HARDCODED_ENDPOINT",
        "MISSING_TIMEOUT",
        "PROCESS_LOCAL_STATE",
    }
    source = inspect.getsource(importlib.import_module(POPULATION_MODULE_NAME))
    assert "scan_and_normalize_semgrep_repository(" in source


def test_population_composes_semgrep_and_incidents_only(
    sqlite_engine: Engine,
    cached_semgrep_scan: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git_calls: list[object] = []
    dependency_calls: list[object] = []
    correlated_signals: list[tuple[NormalizedSignal, ...]] = []
    persist_candidate_calls: list[Candidate] = []
    real_correlate = importlib.import_module(
        "app.candidate_correlation"
    ).correlate_candidates
    real_persist_candidate = persist_candidate

    monkeypatch.setattr(
        "app.git_history_ingestion.scan_and_normalize_git_repository",
        lambda *args, **kwargs: git_calls.append((args, kwargs)) or (),
    )
    monkeypatch.setattr(
        "app.dependency_lifecycle_ingestion.normalize_dependency_lifecycle_finding",
        lambda *args, **kwargs: dependency_calls.append((args, kwargs)),
    )

    def capturing_correlate(normalized_signals: object) -> tuple[Candidate, ...]:
        signals = tuple(normalized_signals)  # type: ignore[arg-type]
        correlated_signals.append(signals)
        return real_correlate(signals)

    def capturing_persist_candidate(
        session: Session,
        candidate: Candidate,
    ) -> object:
        persist_candidate_calls.append(candidate)
        return real_persist_candidate(session, candidate)

    monkeypatch.setattr(
        "app.development_population.correlate_candidates",
        capturing_correlate,
    )
    monkeypatch.setattr(
        "app.development_population.persist_candidate",
        capturing_persist_candidate,
    )

    result = run_development_population(_enabled_settings(), engine=sqlite_engine)

    assert cached_semgrep_scan == list(CONTROLLED_REPOSITORY_ASSET_KEYS)
    assert git_calls == []
    assert dependency_calls == []
    assert result.semgrep_signal_count == 3
    assert result.incident_signal_count == 4
    assert result.signal_created_count + result.signal_duplicate_count == 7
    assert len(correlated_signals) == 1
    assert len(correlated_signals[0]) == 7
    assert result.correlated_candidate_count == 4
    assert len(persist_candidate_calls) == 4
    assert {
        candidate.hypothesis.split(" affecting ", 1)[0]
        for candidate in persist_candidate_calls
    } == {
        "Potential HARDCODED_ENDPOINT issue",
        "Potential MISSING_TIMEOUT issue",
        "Potential PROCESS_LOCAL_STATE issue",
        "Potential recurring operational incident pattern",
    }


def test_unexpected_candidate_count_fails_and_rolls_back(
    sqlite_engine: Engine,
    cached_semgrep_scan: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.development_population.correlate_candidates",
        lambda normalized_signals: (),
    )

    with pytest.raises(DevelopmentPopulationError, match="expected 4 Candidates"):
        run_development_population(_enabled_settings(), engine=sqlite_engine)

    with Session(sqlite_engine) as session:
        assert session.scalar(select(func.count()).select_from(IncidentModel)) == 0
        assert session.scalar(select(func.count()).select_from(SignalModel)) == 0
        assert session.scalar(select(func.count()).select_from(CandidateModel)) == 0


def test_successful_population_commits_once(
    sqlite_engine: Engine,
    cached_semgrep_scan: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit_count = 0
    original_commit = Session.commit

    def tracking_commit(self: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit(self)

    monkeypatch.setattr(Session, "commit", tracking_commit)

    result = run_development_population(_enabled_settings(), engine=sqlite_engine)

    assert commit_count == 1
    assert result == DevelopmentPopulationResult(
        semgrep_signal_count=3,
        incident_signal_count=4,
        signal_created_count=7,
        signal_duplicate_count=0,
        correlated_candidate_count=4,
        candidate_created_count=4,
        candidate_updated_count=0,
        candidate_unchanged_count=0,
    )

    with Session(sqlite_engine) as session:
        assert session.scalar(select(func.count()).select_from(SignalModel)) == 7
        assert session.scalar(select(func.count()).select_from(CandidateModel)) == 4


def test_failure_rolls_back_after_partial_work(
    sqlite_engine: Engine,
    cached_semgrep_scan: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_persist_candidate = persist_candidate
    persist_calls = {"count": 0}

    def fail_after_first(session: Session, candidate: Candidate) -> object:
        persist_calls["count"] += 1
        if persist_calls["count"] == 1:
            return real_persist_candidate(session, candidate)
        raise RuntimeError("candidate persistence failed")

    monkeypatch.setattr(
        "app.development_population.persist_candidate",
        fail_after_first,
    )

    with pytest.raises(RuntimeError, match="candidate persistence failed"):
        run_development_population(_enabled_settings(), engine=sqlite_engine)

    with Session(sqlite_engine) as session:
        assert session.scalar(select(func.count()).select_from(IncidentModel)) == 0
        assert session.scalar(select(func.count()).select_from(SignalModel)) == 0
        assert session.scalar(select(func.count()).select_from(CandidateModel)) == 0


def test_rerun_is_idempotent_for_signals_and_candidates(
    sqlite_engine: Engine,
    cached_semgrep_scan: list[str],
) -> None:
    first = run_development_population(_enabled_settings(), engine=sqlite_engine)
    second = run_development_population(_enabled_settings(), engine=sqlite_engine)

    assert first.signal_created_count == 7
    assert first.candidate_created_count == 4
    assert second == DevelopmentPopulationResult(
        semgrep_signal_count=3,
        incident_signal_count=4,
        signal_created_count=0,
        signal_duplicate_count=7,
        correlated_candidate_count=4,
        candidate_created_count=0,
        candidate_updated_count=0,
        candidate_unchanged_count=4,
    )

    with Session(sqlite_engine) as session:
        signal_ids = set(session.scalars(select(SignalModel.signal_id)))
        candidate_ids = set(session.scalars(select(CandidateModel.candidate_id)))
        assert len(signal_ids) == 7
        assert len(candidate_ids) == 4

    third = run_development_population(_enabled_settings(), engine=sqlite_engine)
    assert third.candidate_unchanged_count == 4

    with Session(sqlite_engine) as session:
        assert (
            set(session.scalars(select(CandidateModel.candidate_id))) == candidate_ids
        )
        assert set(session.scalars(select(SignalModel.signal_id))) == signal_ids


def test_summary_does_not_print_secrets(
    sqlite_engine: Engine,
    cached_semgrep_scan: list[str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.development_population.settings",
        _enabled_settings(),
    )
    monkeypatch.setattr(
        "app.development_population.create_database_engine",
        lambda app_settings: sqlite_engine,
    )
    monkeypatch.setattr(sqlite_engine, "dispose", lambda: None)

    main()
    output = capsys.readouterr().out

    assert "estate seed complete" in output
    assert "Semgrep observations/signals: 3" in output
    assert "incident signals: 4" in output
    assert "correlated Candidates: 4" in output
    assert "commit success" in output
    assert "DATABASE_URL" not in output
    assert "odbc" not in output.lower()
    assert "password" not in output.lower()
    assert "secret" not in output.lower()


def test_population_does_not_create_technical_debt(
    sqlite_engine: Engine,
    cached_semgrep_scan: list[str],
) -> None:
    source = inspect.getsource(importlib.import_module(POPULATION_MODULE_NAME))
    imported = _imported_module_names(source)
    result = run_development_population(_enabled_settings(), engine=sqlite_engine)

    assert not any("technical_debt" in name.lower() for name in imported)
    assert result.correlated_candidate_count == 4
    with Session(sqlite_engine) as session:
        assert session.scalar(select(func.count()).select_from(CandidateModel)) == 4
        assert "technical_debt" not in CandidateModel.__table__.columns.keys()
