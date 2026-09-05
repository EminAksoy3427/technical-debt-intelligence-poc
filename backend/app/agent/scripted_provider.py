from collections.abc import Sequence

from app.agent.runtime_contracts import (
    InvestigationRuntimeContext,
    ProviderStep,
)


class ScriptedProviderExhaustedError(RuntimeError):
    """The deterministic script ended without a final decision."""


class ScriptedInvestigationProvider:
    """Deterministic provider used to prove runtime mechanics without an LLM."""

    def __init__(self, steps: Sequence[ProviderStep | Exception]) -> None:
        self._steps = tuple(steps)
        self._next_step_index = 0
        self._received_contexts: list[InvestigationRuntimeContext] = []

    @property
    def received_contexts(self) -> tuple[InvestigationRuntimeContext, ...]:
        return tuple(self._received_contexts)

    def next_step(self, context: InvestigationRuntimeContext) -> ProviderStep:
        self._received_contexts.append(context)
        if self._next_step_index >= len(self._steps):
            raise ScriptedProviderExhaustedError(
                "Scripted provider has no remaining decision"
            )

        step = self._steps[self._next_step_index]
        self._next_step_index += 1
        if isinstance(step, Exception):
            raise step
        return step
