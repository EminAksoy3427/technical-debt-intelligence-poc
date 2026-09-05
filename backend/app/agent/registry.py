from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from pydantic import BaseModel

from app.agent.contracts import ToolRegistration


@dataclass(frozen=True)
class ToolRegistry:
    """Deterministic in-code collection of explicit tool registrations."""

    registrations: tuple[ToolRegistration[BaseModel, BaseModel], ...]
    _registrations_by_id: Mapping[
        str, ToolRegistration[BaseModel, BaseModel]
    ] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        registrations_by_id: dict[
            str, ToolRegistration[BaseModel, BaseModel]
        ] = {}
        for registration in self.registrations:
            tool_id = registration.descriptor.tool_id
            if tool_id in registrations_by_id:
                raise ValueError(f"Duplicate tool identifier: {tool_id}")
            registrations_by_id[tool_id] = registration

        ordered = tuple(
            sorted(
                self.registrations,
                key=lambda registration: registration.descriptor.tool_id,
            )
        )
        object.__setattr__(self, "registrations", ordered)
        object.__setattr__(
            self,
            "_registrations_by_id",
            MappingProxyType(registrations_by_id),
        )

    def list(self) -> tuple[ToolRegistration[BaseModel, BaseModel], ...]:
        return self.registrations

    def get(self, tool_id: str) -> ToolRegistration[BaseModel, BaseModel]:
        try:
            return self._registrations_by_id[tool_id]
        except KeyError:
            raise KeyError(f"Unknown tool identifier: {tool_id}") from None
