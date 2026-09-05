from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ToolEffect(StrEnum):
    READ = "READ"
    WRITE = "WRITE"


class ToolRisk(StrEnum):
    LOW = "LOW"
    ELEVATED = "ELEVATED"


@dataclass(frozen=True)
class ToolDescriptor:
    """Minimal immutable metadata used for tool policy decisions."""

    tool_id: str
    version: str
    description: str
    effect: ToolEffect
    risk: ToolRisk
    required_scopes: frozenset[str]

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.tool_id, "Tool identifier"),
            (self.version, "Tool version"),
            (self.description, "Tool description"),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if not isinstance(self.effect, ToolEffect):
            raise ValueError("Tool effect must be supported")
        if not isinstance(self.risk, ToolRisk):
            raise ValueError("Tool risk must be supported")

        required_scopes = frozenset(self.required_scopes)
        if any(not scope.strip() for scope in required_scopes):
            raise ValueError("Tool required scopes must not contain blanks")
        object.__setattr__(self, "required_scopes", required_scopes)


class CandidateToolInput(BaseModel):
    """Validated Candidate identity supplied to a governed Candidate tool."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID


type ToolExecutor[InputModelT: BaseModel, ResultModelT: BaseModel] = Callable[
    [InputModelT], ResultModelT
]


@dataclass(frozen=True)
class ToolRegistration[InputModelT: BaseModel, ResultModelT: BaseModel]:
    """Explicit association of tool metadata, schemas, and executor."""

    descriptor: ToolDescriptor
    input_model: type[InputModelT]
    result_model: type[ResultModelT]
    executor: ToolExecutor[InputModelT, ResultModelT]

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ToolDescriptor):
            raise ValueError("Tool registration must have a valid descriptor")
        if not issubclass(self.input_model, BaseModel):
            raise ValueError("Tool input model must be a Pydantic model")
        if not issubclass(self.result_model, BaseModel):
            raise ValueError("Tool result model must be a Pydantic model")
        if not callable(self.executor):
            raise ValueError("Tool registration executor must be callable")
