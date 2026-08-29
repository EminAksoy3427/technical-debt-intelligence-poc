from sqlalchemy import UniqueConstraint

from app.infrastructure.database.base import Base
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel


def _unique_column_sets(table_name: str) -> set[frozenset[str]]:
    table = Base.metadata.tables[table_name]
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_signal_model_preserves_only_canonical_signal_fields() -> None:
    table = SignalModel.__table__

    assert set(table.columns.keys()) == {
        "signal_id",
        "source_system",
        "source_record_id",
        "detected_at",
        "signal_type",
        "affected_asset_id",
        "severity",
    }
    assert frozenset({"source_system", "source_record_id"}) in _unique_column_sets(
        "signals"
    )
    assert {
        foreign_key.target_fullname for foreign_key in table.foreign_keys
    } == {"enterprise_assets.id"}
    assert {"candidate_id", "risk", "validation_status"}.isdisjoint(
        table.columns.keys()
    )


def test_evidence_model_preserves_evidence_without_validation_fields() -> None:
    table = EvidenceModel.__table__

    assert set(table.columns.keys()) == {
        "evidence_id",
        "signal_id",
        "source_system",
        "source_reference",
        "captured_at",
        "reference_uri",
    }
    assert {
        foreign_key.target_fullname for foreign_key in table.foreign_keys
    } == {"signals.signal_id"}
    assert {"validated", "validation_status", "validated_by"}.isdisjoint(
        table.columns.keys()
    )


def test_signal_and_evidence_models_have_no_candidate_relationship() -> None:
    signal_foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in SignalModel.__table__.foreign_keys
    }
    evidence_foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in EvidenceModel.__table__.foreign_keys
    }

    assert not any("candidate" in target for target in signal_foreign_keys)
    assert not any("candidate" in target for target in evidence_foreign_keys)
    assert not any("candidate" in table_name for table_name in Base.metadata.tables)
