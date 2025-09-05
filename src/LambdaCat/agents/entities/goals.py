"""Goal and intention definitions for agent entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ..actions import Plan  # Plan DSL AST type

S = TypeVar("S")  # State type


@dataclass(frozen=True)
class Goal(Generic[S]):
    """An agent goal with parameters and constraints."""

    name: str
    params: dict[str, object]
    priority: float = 1.0
    deadline: float | None = None
    constraints: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if self.constraints is None:
            object.__setattr__(self, "constraints", {})


@dataclass(frozen=True)
class Intention(Generic[S]):
    """An intention to execute a plan to achieve a goal."""

    goal: Goal[S]
    plan_ast: Plan
    evaluator: Callable[[dict[str, object]], float] | None = None
    confidence: float = 1.0
    metadata: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

    def evaluate(self, context: dict[str, object]) -> float:
        """Evaluate this intention given context."""
        if self.evaluator is not None:
            return self.evaluator(context)
        return self.confidence
