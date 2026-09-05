from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.domain.signals import SourceObservationRef


@dataclass(frozen=True)
class ConnectorDescriptor:
    """Stable metadata for one explicitly registered source connector."""

    connector_id: str
    display_name: str
    version: str
    source_system: str
    transport: str
    read_only: bool

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.connector_id, "Connector identifier"),
            (self.display_name, "Connector display name"),
            (self.version, "Connector version"),
            (self.source_system, "Connector source system"),
            (self.transport, "Connector transport"),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if not isinstance(self.read_only, bool):
            raise ValueError("Connector read-only flag must be a boolean")


@dataclass(frozen=True)
class SourceObservation[SourceRecord]:
    """Acquired source record with its exact identity and observation time."""

    provenance: SourceObservationRef
    observed_at: datetime
    record: SourceRecord

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, SourceObservationRef):
            raise ValueError("Source observation must have valid provenance")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("Source observation timestamp must be timezone-aware")


type SourceConnector[SourceConfiguration, SourceRecord] = Callable[
    [SourceConfiguration],
    tuple[SourceObservation[SourceRecord], ...],
]


@dataclass(frozen=True)
class ConnectorRegistration[SourceConfiguration, SourceRecord]:
    """Explicit composition of connector metadata and acquisition callable."""

    descriptor: ConnectorDescriptor
    acquire: SourceConnector[SourceConfiguration, SourceRecord]

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ConnectorDescriptor):
            raise ValueError("Connector registration must have a valid descriptor")
        if not callable(self.acquire):
            raise ValueError("Connector registration acquisition must be callable")
