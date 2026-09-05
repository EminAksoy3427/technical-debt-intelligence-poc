from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Final

from app.connectors.contracts import ConnectorRegistration
from app.connectors.dependency_lifecycle import DEPENDENCY_LIFECYCLE_CONNECTOR
from app.infrastructure.dependency_lifecycle import DependencyLifecycleFinding


@dataclass(frozen=True)
class ConnectorRegistry[SourceConfiguration, SourceRecord]:
    """Deterministic in-code collection of explicit connector registrations."""

    registrations: tuple[
        ConnectorRegistration[SourceConfiguration, SourceRecord], ...
    ]
    _registrations_by_id: Mapping[
        str, ConnectorRegistration[SourceConfiguration, SourceRecord]
    ] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        registrations_by_id: dict[
            str, ConnectorRegistration[SourceConfiguration, SourceRecord]
        ] = {}
        for registration in self.registrations:
            connector_id = registration.descriptor.connector_id
            if connector_id in registrations_by_id:
                raise ValueError(f"Duplicate connector identifier: {connector_id}")
            registrations_by_id[connector_id] = registration
        object.__setattr__(
            self,
            "_registrations_by_id",
            MappingProxyType(registrations_by_id),
        )

    def list(self) -> tuple[
        ConnectorRegistration[SourceConfiguration, SourceRecord], ...
    ]:
        return self.registrations

    def get(
        self,
        connector_id: str,
    ) -> ConnectorRegistration[SourceConfiguration, SourceRecord]:
        try:
            return self._registrations_by_id[connector_id]
        except KeyError:
            raise KeyError(f"Unknown connector identifier: {connector_id}") from None


CONNECTOR_REGISTRY: Final = ConnectorRegistry[Path, DependencyLifecycleFinding](
    registrations=(DEPENDENCY_LIFECYCLE_CONNECTOR,),
)


def list_connectors() -> tuple[
    ConnectorRegistration[Path, DependencyLifecycleFinding], ...
]:
    return CONNECTOR_REGISTRY.list()


def get_connector(
    connector_id: str,
) -> ConnectorRegistration[Path, DependencyLifecycleFinding]:
    return CONNECTOR_REGISTRY.get(connector_id)
