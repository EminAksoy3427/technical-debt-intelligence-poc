from dataclasses import dataclass

from app.domain.signals import Evidence, Signal, SourceObservationRef


@dataclass(frozen=True)
class NormalizedSignal:
    """Canonical output produced by a source adapter's deterministic normalization."""

    signal: Signal
    evidence: frozenset[Evidence]

    def __post_init__(self) -> None:
        evidence = frozenset(self.evidence)
        if not evidence:
            raise ValueError("A normalized Signal must include Evidence")

        evidence_ids = frozenset(item.evidence_id for item in evidence)
        if len(evidence_ids) != len(evidence):
            raise ValueError("Normalized Signal Evidence identifiers must be unique")
        if evidence_ids != self.signal.evidence_ids:
            raise ValueError(
                "Normalized Signal Evidence must match the Signal evidence identifiers"
            )

        object.__setattr__(self, "evidence", evidence)

    @property
    def provenance(self) -> SourceObservationRef:
        return self.signal.provenance
