"""Intention policy for mapping goals to plans."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ..cognition.memory import AgentState
from ..cognition.policy import EvaluationResult, Policy
from .goals import Goal, Intention

S = TypeVar("S")  # State type


class IntentionPolicy(Policy[S, Intention[S]], ABC, Generic[S]):
    """Policy for mapping goals to intentions (plans)."""

    @abstractmethod
    def propose_intentions(
        self,
        goals: list[Goal[S]],
        state: AgentState[S],
        context: dict[str, object]
    ) -> list[Intention[S]]:
        """Propose candidate intentions for given goals and state."""
        pass

    def evaluate(
        self,
        state: S,
        intention: Intention[S],
        context: dict[str, object]
    ) -> EvaluationResult[S]:
        """Evaluate an intention given state and context."""
        score = intention.evaluate(context)
        confidence = intention.confidence

        return EvaluationResult(
            score=score,
            confidence=confidence,
            reasoning=f"Intention for goal '{intention.goal.name}'",
            metadata={
                "goal_name": intention.goal.name,
                "goal_priority": intention.goal.priority,
                "intention_confidence": intention.confidence
            }
        )

    def select_action(
        self,
        state: S,
        available_actions: list[Intention[S]],
        context: dict[str, object]
    ) -> Intention[S]:
        """Select the best intention from available options."""
        if not available_actions:
            raise ValueError("No intentions available")

        # Evaluate all intentions
        evaluations = [
            (intention, self.evaluate(state, intention, context))
            for intention in available_actions
        ]

        # Sort by score (descending) and confidence (descending)
        evaluations.sort(key=lambda x: (x[1].score, x[1].confidence), reverse=True)

        return evaluations[0][0]


class SimpleIntentionPolicy(IntentionPolicy[S], Generic[S]):
    """Simple intention policy that maps goals to basic plans."""

    def __init__(
        self,
        goal_to_plan: dict[str, object] | None = None,
        default_confidence: float = 0.8
    ):
        self.goal_to_plan = goal_to_plan or {}
        self.default_confidence = default_confidence

    def propose_intentions(
        self,
        goals: list[Goal[S]],
        state: AgentState[S],
        context: dict[str, object]
    ) -> list[Intention[S]]:
        """Propose intentions by mapping goals to plans."""
        intentions = []

        for goal in goals:
            if goal.name in self.goal_to_plan:
                plan_ast = self.goal_to_plan[goal.name]
                intention = Intention(
                    goal=goal,
                    plan_ast=plan_ast,
                    confidence=self.default_confidence,
                    metadata={"policy": "simple", "goal_params": goal.params}
                )
                intentions.append(intention)

        return intentions
