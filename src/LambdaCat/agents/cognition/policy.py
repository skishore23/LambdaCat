from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from .beliefs import BeliefSystem

S = TypeVar("S")  # State type
A = TypeVar("A")  # Action type


@dataclass(frozen=True)
class EvaluationResult(Generic[S]):
    """Result of policy evaluation."""

    score: float
    confidence: float
    reasoning: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata
        }


class Policy(ABC, Generic[S, A]):
    """Abstract base class for agent policies."""

    @abstractmethod
    def evaluate(self, state: S, action: A, context: dict[str, Any]) -> EvaluationResult[S]:
        """Evaluate an action given a state."""
        pass

    @abstractmethod
    def select_action(self, state: S, available_actions: list[A], context: dict[str, Any]) -> A:
        """Select the best action from available options."""
        pass


class UtilityModel(ABC, Generic[S]):
    """Abstract base class for utility models."""

    @abstractmethod
    def compute_utility(self, state: S, context: dict[str, Any]) -> float:
        """Compute utility of a state."""
        pass


class BeliefBasedPolicy(Policy[S, A]):
    """Policy that uses beliefs to make decisions."""

    def __init__(self, belief_system: BeliefSystem[S], utility_model: UtilityModel[S]):
        self.belief_system = belief_system
        self.utility_model = utility_model

    def evaluate(self, state: S, action: A, context: dict[str, Any]) -> EvaluationResult[S]:
        """Evaluate action based on beliefs and utility."""
        # Get relevant beliefs
        action_key = f"action_{action}_good"
        belief = self.belief_system.get_belief(action_key)

        if belief is None:
            score = 0.5  # Neutral if no belief
            confidence = 0.0
            reasoning = f"No belief about action {action}"
        else:
            score = belief.to_probability()
            confidence = belief.confidence
            reasoning = f"Belief: {belief.proposition} (logit={belief.logit:.2f})"

        # Adjust by utility
        utility = self.utility_model.compute_utility(state, context)
        adjusted_score = score * (1.0 + utility * 0.1)  # Small utility adjustment

        return EvaluationResult(
            score=adjusted_score,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "belief_logit": belief.logit if belief else 0.0,
                "utility": utility,
                "action": str(action)
            }
        )

    def select_action(self, state: S, available_actions: list[A], context: dict[str, Any]) -> A:
        """Select action with highest evaluation score."""
        if not available_actions:
            raise ValueError("No actions available")

        evaluations = []
        for action in available_actions:
            result = self.evaluate(state, action, context)
            evaluations.append((action, result))

        # Sort by score (descending)
        evaluations.sort(key=lambda x: x[1].score, reverse=True)

        return evaluations[0][0]


class SimpleUtilityModel(UtilityModel[S]):
    """Simple utility model based on state properties."""

    def __init__(self, utility_functions: dict[str, Callable[[S], float]]):
        self.utility_functions = utility_functions

    def compute_utility(self, state: S, context: dict[str, Any]) -> float:
        """Compute utility as weighted sum of utility functions."""
        total_utility = 0.0
        total_weight = 0.0

        for name, func in self.utility_functions.items():
            try:
                utility = func(state)
                weight = context.get(f"weight_{name}", 1.0)
                total_utility += utility * weight
                total_weight += weight
            except Exception:
                continue  # Skip failed utility functions

        return total_utility / total_weight if total_weight > 0 else 0.0


class RewardBasedPolicy(Policy[S, A]):
    """Policy that learns from rewards."""

    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.action_values: dict[str, float] = {}

    def get_action_key(self, state: S, action: A) -> str:
        """Generate key for action-value lookup."""
        return f"{state}_{action}"

    def evaluate(self, state: S, action: A, context: dict[str, Any]) -> EvaluationResult[S]:
        """Evaluate action based on learned values."""
        action_key = self.get_action_key(state, action)
        value = self.action_values.get(action_key, 0.0)

        # Convert value to probability-like score
        score = 1.0 / (1.0 + math.exp(-value))

        return EvaluationResult(
            score=score,
            confidence=min(1.0, abs(value) / 10.0),  # Confidence based on value magnitude
            reasoning=f"Learned value: {value:.2f}",
            metadata={
                "action_value": value,
                "action_key": action_key
            }
        )

    def select_action(self, state: S, available_actions: list[A], context: dict[str, Any]) -> A:
        """Select action with highest learned value."""
        if not available_actions:
            raise ValueError("No actions available")

        evaluations = []
        for action in available_actions:
            result = self.evaluate(state, action, context)
            evaluations.append((action, result))

        # Sort by score (descending)
        evaluations.sort(key=lambda x: x[1].score, reverse=True)

        return evaluations[0][0]

    def update(self, state: S, action: A, reward: float, next_state: S = None):
        """Update action values based on reward."""
        action_key = self.get_action_key(state, action)
        current_value = self.action_values.get(action_key, 0.0)

        # Q-learning update
        if next_state is not None:
            # Find max value for next state
            next_state_key = str(next_state)
            max_next_value = max(
                (self.action_values.get(f"{next_state_key}_{a}", 0.0) for a in [action]),
                default=0.0
            )
            target = reward + self.discount_factor * max_next_value
        else:
            target = reward

        # Update value
        new_value = current_value + self.learning_rate * (target - current_value)
        self.action_values[action_key] = new_value


class EpsilonGreedyPolicy(Policy[S, A]):
    """Epsilon-greedy exploration policy."""

    def __init__(self, base_policy: Policy[S, A], epsilon: float = 0.1):
        self.base_policy = base_policy
        self.epsilon = epsilon

    def evaluate(self, state: S, action: A, context: dict[str, Any]) -> EvaluationResult[S]:
        """Evaluate using base policy."""
        return self.base_policy.evaluate(state, action, context)

    def select_action(self, state: S, available_actions: list[A], context: dict[str, Any]) -> A:
        """Select action with epsilon-greedy strategy."""
        import random

        if random.random() < self.epsilon:
            # Explore: random action
            return random.choice(available_actions)
        else:
            # Exploit: use base policy
            return self.base_policy.select_action(state, available_actions, context)


class MultiObjectivePolicy(Policy[S, A]):
    """Policy that optimizes multiple objectives."""

    def __init__(self, objectives: list[Callable[[S, A], float]], weights: list[float] = None):
        self.objectives = objectives
        self.weights = weights or [1.0] * len(objectives)

        if len(self.weights) != len(self.objectives):
            raise ValueError("Number of weights must match number of objectives")

    def evaluate(self, state: S, action: A, context: dict[str, Any]) -> EvaluationResult[S]:
        """Evaluate action across multiple objectives."""
        scores = []
        reasoning_parts = []

        for i, objective in enumerate(self.objectives):
            try:
                score = objective(state, action)
                weight = self.weights[i]
                weighted_score = score * weight
                scores.append(weighted_score)
                reasoning_parts.append(f"obj{i}: {score:.2f}*{weight:.2f}={weighted_score:.2f}")
            except Exception as e:
                scores.append(0.0)
                reasoning_parts.append(f"obj{i}: error({e})")

        total_score = sum(scores)
        confidence = min(1.0, len([s for s in scores if s > 0]) / len(scores))

        return EvaluationResult(
            score=total_score,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts),
            metadata={
                "objective_scores": scores,
                "weights": self.weights
            }
        )

    def select_action(self, state: S, available_actions: list[A], context: dict[str, Any]) -> A:
        """Select action with highest multi-objective score."""
        if not available_actions:
            raise ValueError("No actions available")

        evaluations = []
        for action in available_actions:
            result = self.evaluate(state, action, context)
            evaluations.append((action, result))

        # Sort by score (descending)
        evaluations.sort(key=lambda x: x[1].score, reverse=True)

        return evaluations[0][0]


# Policy evaluation utilities
def evaluate_policy_performance(
    policy: Policy[S, A],
    test_states: list[S],
    test_actions: list[list[A]],
    context: dict[str, Any] = None
) -> dict[str, float]:
    """Evaluate policy performance on test data."""
    if context is None:
        context = {}

    total_score = 0.0
    total_confidence = 0.0
    correct_selections = 0

    for state, actions in zip(test_states, test_actions):
        if not actions:
            continue

        # Evaluate all actions
        evaluations = []
        for action in actions:
            result = policy.evaluate(state, action, context)
            evaluations.append((action, result))

        # Find best action
        best_action = max(evaluations, key=lambda x: x[1].score)[0]
        selected_action = policy.select_action(state, actions, context)

        # Check if selection matches best
        if selected_action == best_action:
            correct_selections += 1

        # Accumulate scores
        best_result = max(evaluations, key=lambda x: x[1].score)[1]
        total_score += best_result.score
        total_confidence += best_result.confidence

    num_tests = len([a for a in test_actions if a])

    return {
        "average_score": total_score / num_tests if num_tests > 0 else 0.0,
        "average_confidence": total_confidence / num_tests if num_tests > 0 else 0.0,
        "selection_accuracy": correct_selections / num_tests if num_tests > 0 else 0.0
    }


# Factory functions
def create_belief_based_policy(
    belief_system: BeliefSystem[S],
    utility_functions: dict[str, Callable[[S], float]]
) -> BeliefBasedPolicy[S, A]:
    """Create a belief-based policy."""
    utility_model = SimpleUtilityModel(utility_functions)
    return BeliefBasedPolicy(belief_system, utility_model)


def create_reward_based_policy(
    learning_rate: float = 0.1,
    discount_factor: float = 0.9
) -> RewardBasedPolicy[S, A]:
    """Create a reward-based learning policy."""
    return RewardBasedPolicy(learning_rate, discount_factor)


def create_multi_objective_policy(
    objectives: list[Callable[[S, A], float]],
    weights: list[float] = None
) -> MultiObjectivePolicy[S, A]:
    """Create a multi-objective policy."""
    return MultiObjectivePolicy(objectives, weights)
