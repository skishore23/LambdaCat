from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Generic, TypeVar

S = TypeVar("S")  # State type


@dataclass(frozen=True)
class Belief(Generic[S]):
    """A single belief with metadata."""

    proposition: str
    logit: float  # log-odds
    confidence: float  # 0.0 to 1.0
    source: str  # where this belief came from
    timestamp: float
    decay_rate: float = 0.95  # exponential decay factor

    def to_probability(self) -> float:
        """Convert log-odds to probability."""
        return 1.0 / (1.0 + math.exp(-self.logit))

    def decay(self, current_time: float) -> Belief[S]:
        """Apply exponential decay to the belief."""
        time_diff = current_time - self.timestamp
        decay_factor = self.decay_rate ** time_diff
        return Belief(
            proposition=self.proposition,
            logit=self.logit * decay_factor,
            confidence=self.confidence * decay_factor,
            source=self.source,
            timestamp=current_time,
            decay_rate=self.decay_rate
        )


@dataclass(frozen=True)
class BeliefSystem(Generic[S]):
    """A system for managing weighted beliefs."""

    beliefs: Dict[str, Belief[S]] = None

    def __post_init__(self):
        if self.beliefs is None:
            object.__setattr__(self, 'beliefs', {})

    def add_belief(
        self,
        proposition: str,
        logit: float,
        confidence: float = 1.0,
        source: str = "unknown",
        timestamp: float = None
    ) -> BeliefSystem[S]:
        """Add a new belief to the system."""
        if timestamp is None:
            import time
            timestamp = time.time()

        belief = Belief(
            proposition=proposition,
            logit=logit,
            confidence=confidence,
            source=source,
            timestamp=timestamp
        )

        new_beliefs = dict(self.beliefs)
        new_beliefs[proposition] = belief

        return BeliefSystem(beliefs=new_beliefs)

    def update_belief(
        self,
        proposition: str,
        delta_logit: float,
        source: str = "update",
        timestamp: float = None
    ) -> BeliefSystem[S]:
        """Update an existing belief with new evidence."""
        if timestamp is None:
            import time
            timestamp = time.time()

        current_belief = self.beliefs.get(proposition)
        if current_belief is None:
            # Create new belief
            return self.add_belief(proposition, delta_logit, source=source, timestamp=timestamp)

        # Update existing belief
        new_logit = current_belief.logit + delta_logit
        new_confidence = min(1.0, current_belief.confidence + 0.1)  # Slight confidence increase

        belief = Belief(
            proposition=proposition,
            logit=new_logit,
            confidence=new_confidence,
            source=source,
            timestamp=timestamp,
            decay_rate=current_belief.decay_rate
        )

        new_beliefs = dict(self.beliefs)
        new_beliefs[proposition] = belief

        return BeliefSystem(beliefs=new_beliefs)

    def get_belief(self, proposition: str) -> Belief[S] | None:
        """Get a belief by proposition."""
        return self.beliefs.get(proposition)

    def get_belief_logit(self, proposition: str) -> float:
        """Get belief strength as log-odds."""
        belief = self.beliefs.get(proposition)
        return belief.logit if belief else 0.0

    def get_belief_probability(self, proposition: str) -> float:
        """Get belief as probability."""
        belief = self.beliefs.get(proposition)
        return belief.to_probability() if belief else 0.5

    def decay_all_beliefs(self, current_time: float = None) -> BeliefSystem[S]:
        """Apply decay to all beliefs."""
        if current_time is None:
            import time
            current_time = time.time()

        new_beliefs = {}
        for prop, belief in self.beliefs.items():
            decayed = belief.decay(current_time)
            if decayed.logit > -10.0:  # Keep beliefs that aren't too weak
                new_beliefs[prop] = decayed

        return BeliefSystem(beliefs=new_beliefs)

    def normalize_beliefs(self, max_logit: float = 10.0) -> BeliefSystem[S]:
        """Normalize beliefs to prevent extreme values."""
        new_beliefs = {}
        for prop, belief in self.beliefs.items():
            normalized_logit = max(-max_logit, min(max_logit, belief.logit))
            normalized_belief = Belief(
                proposition=belief.proposition,
                logit=normalized_logit,
                confidence=belief.confidence,
                source=belief.source,
                timestamp=belief.timestamp,
                decay_rate=belief.decay_rate
            )
            new_beliefs[prop] = normalized_belief

        return BeliefSystem(beliefs=new_beliefs)

    def merge_beliefs(self, other: BeliefSystem[S], strategy: str = "weighted_average") -> BeliefSystem[S]:
        """Merge beliefs from another system."""
        new_beliefs = dict(self.beliefs)

        for prop, other_belief in other.beliefs.items():
            if prop in new_beliefs:
                # Merge existing belief
                current_belief = new_beliefs[prop]
                if strategy == "weighted_average":
                    # Weight by confidence
                    total_confidence = current_belief.confidence + other_belief.confidence
                    if total_confidence > 0:
                        weight1 = current_belief.confidence / total_confidence
                        weight2 = other_belief.confidence / total_confidence
                        merged_logit = weight1 * current_belief.logit + weight2 * other_belief.logit
                        merged_confidence = min(1.0, (current_belief.confidence + other_belief.confidence) / 2)
                    else:
                        merged_logit = (current_belief.logit + other_belief.logit) / 2
                        merged_confidence = 0.5
                elif strategy == "max_confidence":
                    # Take the belief with higher confidence
                    if other_belief.confidence > current_belief.confidence:
                        merged_logit = other_belief.logit
                        merged_confidence = other_belief.confidence
                    else:
                        merged_logit = current_belief.logit
                        merged_confidence = current_belief.confidence
                else:
                    # Simple average
                    merged_logit = (current_belief.logit + other_belief.logit) / 2
                    merged_confidence = min(1.0, (current_belief.confidence + other_belief.confidence) / 2)

                merged_belief = Belief(
                    proposition=prop,
                    logit=merged_logit,
                    confidence=merged_confidence,
                    source=f"merge({current_belief.source},{other_belief.source})",
                    timestamp=max(current_belief.timestamp, other_belief.timestamp),
                    decay_rate=current_belief.decay_rate
                )
                new_beliefs[prop] = merged_belief
            else:
                # Add new belief
                new_beliefs[prop] = other_belief

        return BeliefSystem(beliefs=new_beliefs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            prop: {
                "logit": belief.logit,
                "confidence": belief.confidence,
                "source": belief.source,
                "timestamp": belief.timestamp,
                "decay_rate": belief.decay_rate
            }
            for prop, belief in self.beliefs.items()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BeliefSystem[S]:
        """Create from dictionary."""
        beliefs = {}
        for prop, belief_data in data.items():
            belief = Belief(
                proposition=prop,
                logit=belief_data["logit"],
                confidence=belief_data["confidence"],
                source=belief_data["source"],
                timestamp=belief_data["timestamp"],
                decay_rate=belief_data.get("decay_rate", 0.95)
            )
            beliefs[prop] = belief

        return cls(beliefs=beliefs)


# Belief update functions
def bayesian_update(
    prior_logit: float,
    evidence_logit: float,
    prior_confidence: float = 1.0,
    evidence_confidence: float = 1.0
) -> tuple[float, float]:
    """Bayesian belief update in log-odds space.
    
    Args:
        prior_logit: Prior belief as log-odds
        evidence_logit: Evidence strength as log-odds
        prior_confidence: Prior confidence (0.0 to 1.0)
        evidence_confidence: Evidence confidence (0.0 to 1.0)
        
    Returns:
        (updated_logit, updated_confidence)
    """
    # Weighted combination
    total_confidence = prior_confidence + evidence_confidence
    if total_confidence > 0:
        weight_prior = prior_confidence / total_confidence
        weight_evidence = evidence_confidence / total_confidence
        updated_logit = weight_prior * prior_logit + weight_evidence * evidence_logit
        updated_confidence = min(1.0, total_confidence / 2)
    else:
        updated_logit = (prior_logit + evidence_logit) / 2
        updated_confidence = 0.5

    return updated_logit, updated_confidence


def evidence_to_logit(probability: float) -> float:
    """Convert probability to log-odds."""
    if probability <= 0.0:
        return -10.0  # Very negative
    elif probability >= 1.0:
        return 10.0   # Very positive
    else:
        return math.log(probability / (1.0 - probability))


def logit_to_probability(logit: float) -> float:
    """Convert log-odds to probability."""
    return 1.0 / (1.0 + math.exp(-logit))


# Belief system utilities
def create_belief_system() -> BeliefSystem[S]:
    """Create an empty belief system."""
    return BeliefSystem()


def create_belief_system_from_dict(data: Dict[str, Any]) -> BeliefSystem[S]:
    """Create a belief system from dictionary data."""
    return BeliefSystem.from_dict(data)


# Integration with AgentState
def integrate_with_agent_state(agent_state: Any) -> BeliefSystem[S]:
    """Extract belief system from AgentState."""
    if hasattr(agent_state, 'beliefs') and isinstance(agent_state.beliefs, dict):
        # Convert simple dict to BeliefSystem
        beliefs = {}
        for prop, logit in agent_state.beliefs.items():
            belief = Belief(
                proposition=prop,
                logit=logit,
                confidence=1.0,
                source="agent_state",
                timestamp=0.0
            )
            beliefs[prop] = belief
        return BeliefSystem(beliefs=beliefs)
    else:
        return create_belief_system()
