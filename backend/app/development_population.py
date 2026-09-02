"""Fixed vertical-slice development population for Candidates.

This command composes existing application functions to seed the enterprise
estate, ingest controlled Semgrep findings and seeded incidents, persist
Signals, correlate deterministic Candidates, and persist those Candidates.

It is a development-only vertical slice, not the complete ingestion-source
inventory. It does not create TechnicalDebt and does not validate Candidates.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.candidate_correlation import correlate_candidates
from app.core.config import Settings, settings
from app.domain.candidates import Candidate
from app.incident_ingestion import normalize_incident
from app.infrastructure.database.candidate_persistence import (
    CandidatePersistenceResult,
    persist_candidate,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.incident_loading import (
    load_incidents_with_affected_assets,
)
from app.infrastructure.database.signal_persistence import (
    SignalPersistenceResult,
    persist_normalized_signal,
)
from app.semgrep_ingestion import scan_and_normalize_semgrep_repository
from app.signal_ingestion import NormalizedSignal

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent
_CONTROLLED_REPOSITORY_ROOT = _PROJECT_ROOT / "synthetic_repositories"
_SEMGREP_RULES_PATH = _BACKEND_ROOT / "semgrep" / "rules.yml"
_CONTROLLED_REPOSITORY_ASSET_KEYS = (
    "repo-asteria-editor",
    "repo-borealis-renderer",
    "repo-orbit-catalog",
)
_SEMGREP_DETECTED_AT = datetime(2026, 8, 29, 12, 30, tzinfo=UTC)
_EXPECTED_SEMGREP_SIGNAL_COUNT = 3
_EXPECTED_INCIDENT_SIGNAL_COUNT = 4
_EXPECTED_CONTROLLED_SIGNAL_COUNT = 7
_EXPECTED_CANDIDATE_COUNT = 4
_EXPECTED_HYPOTHESIS_PREFIXES = (
    "Potential HARDCODED_ENDPOINT issue affecting ",
    "Potential MISSING_TIMEOUT issue affecting ",
    "Potential PROCESS_LOCAL_STATE issue affecting ",
    "Potential recurring operational incident pattern affecting ",
)


class DevelopmentPopulationDisabledError(RuntimeError):
    """Raised when development population is not explicitly enabled."""


class DevelopmentPopulationError(RuntimeError):
    """Raised when the fixed development dataset is not produced."""


@dataclass(frozen=True)
class DevelopmentPopulationResult:
    semgrep_signal_count: int
    incident_signal_count: int
    signal_created_count: int
    signal_duplicate_count: int
    correlated_candidate_count: int
    candidate_created_count: int
    candidate_updated_count: int
    candidate_unchanged_count: int


def populate_development_candidates(
    session: Session,
    *,
    app_settings: Settings,
) -> DevelopmentPopulationResult:
    """Compose the fixed development population inside a caller-owned session."""
    _require_development_population_enabled(app_settings)

    seed_enterprise_estate(session)

    semgrep_signals = _scan_controlled_semgrep_signals()
    if len(semgrep_signals) != _EXPECTED_SEMGREP_SIGNAL_COUNT:
        raise DevelopmentPopulationError(
            "Development population expected "
            f"{_EXPECTED_SEMGREP_SIGNAL_COUNT} Semgrep Signals, "
            f"got {len(semgrep_signals)}"
        )

    incident_signals = _normalize_seeded_incidents(session)
    if len(incident_signals) != _EXPECTED_INCIDENT_SIGNAL_COUNT:
        raise DevelopmentPopulationError(
            "Development population expected "
            f"{_EXPECTED_INCIDENT_SIGNAL_COUNT} incident Signals, "
            f"got {len(incident_signals)}"
        )

    normalized_signals = semgrep_signals + incident_signals
    if len(normalized_signals) != _EXPECTED_CONTROLLED_SIGNAL_COUNT:
        raise DevelopmentPopulationError(
            "Development population expected "
            f"{_EXPECTED_CONTROLLED_SIGNAL_COUNT} controlled Signals, "
            f"got {len(normalized_signals)}"
        )

    signal_results = Counter(
        persist_normalized_signal(session, normalized_signal)
        for normalized_signal in normalized_signals
    )

    candidates = correlate_candidates(normalized_signals)
    _require_expected_candidates(candidates)

    candidate_results = Counter(
        persist_candidate(session, candidate) for candidate in candidates
    )

    return DevelopmentPopulationResult(
        semgrep_signal_count=len(semgrep_signals),
        incident_signal_count=len(incident_signals),
        signal_created_count=signal_results[SignalPersistenceResult.CREATED],
        signal_duplicate_count=signal_results[SignalPersistenceResult.DUPLICATE],
        correlated_candidate_count=len(candidates),
        candidate_created_count=candidate_results[CandidatePersistenceResult.CREATED],
        candidate_updated_count=candidate_results[CandidatePersistenceResult.UPDATED],
        candidate_unchanged_count=candidate_results[
            CandidatePersistenceResult.UNCHANGED
        ],
    )


def run_development_population(
    app_settings: Settings,
    *,
    engine: Engine | None = None,
) -> DevelopmentPopulationResult:
    """Run development population in one explicit transaction and commit once."""
    _require_development_population_enabled(app_settings)

    owned_engine = engine is None
    db_engine = engine if engine is not None else create_database_engine(app_settings)
    try:
        with Session(db_engine) as session:
            try:
                result = populate_development_candidates(
                    session,
                    app_settings=app_settings,
                )
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise
    finally:
        if owned_engine:
            db_engine.dispose()


def main() -> None:
    """Entry point for `python -m app.development_population`."""
    result = run_development_population(settings)
    _print_summary(result)


def _require_development_population_enabled(app_settings: Settings) -> None:
    if not app_settings.allow_development_data_population:
        raise DevelopmentPopulationDisabledError(
            "Development candidate population is disabled. Set "
            "ALLOW_DEVELOPMENT_DATA_POPULATION=true to run this fixed "
            "vertical-slice development command."
        )


def _scan_controlled_semgrep_signals() -> tuple[NormalizedSignal, ...]:
    return tuple(
        normalized_signal
        for asset_key in _CONTROLLED_REPOSITORY_ASSET_KEYS
        for normalized_signal in scan_and_normalize_semgrep_repository(
            _CONTROLLED_REPOSITORY_ROOT / asset_key,
            repository_asset_key=asset_key,
            detected_at=_SEMGREP_DETECTED_AT,
            rules_path=_SEMGREP_RULES_PATH,
        )
    )


def _normalize_seeded_incidents(session: Session) -> tuple[NormalizedSignal, ...]:
    return tuple(
        normalize_incident(
            incident,
            primary_affected_asset=affected_asset,
        )
        for incident, affected_asset in load_incidents_with_affected_assets(session)
    )


def _require_expected_candidates(candidates: tuple[Candidate, ...]) -> None:
    if len(candidates) != _EXPECTED_CANDIDATE_COUNT:
        raise DevelopmentPopulationError(
            "Development population expected "
            f"{_EXPECTED_CANDIDATE_COUNT} Candidates, got {len(candidates)}"
        )

    unmatched = list(candidates)
    for prefix in _EXPECTED_HYPOTHESIS_PREFIXES:
        matches = [
            candidate
            for candidate in unmatched
            if candidate.hypothesis.startswith(prefix)
        ]
        if len(matches) != 1:
            raise DevelopmentPopulationError(
                "Development population expected exactly one Candidate whose "
                f"hypothesis starts with {prefix!r}"
            )
        unmatched.remove(matches[0])


def _print_summary(result: DevelopmentPopulationResult) -> None:
    print("estate seed complete")
    print(f"Semgrep observations/signals: {result.semgrep_signal_count}")
    print(f"incident signals: {result.incident_signal_count}")
    print(
        "Signal persistence "
        f"CREATED={result.signal_created_count} "
        f"DUPLICATE={result.signal_duplicate_count}"
    )
    print(f"correlated Candidates: {result.correlated_candidate_count}")
    print(
        "Candidate persistence "
        f"CREATED={result.candidate_created_count} "
        f"UPDATED={result.candidate_updated_count} "
        f"UNCHANGED={result.candidate_unchanged_count}"
    )
    print("commit success")


if __name__ == "__main__":
    main()
