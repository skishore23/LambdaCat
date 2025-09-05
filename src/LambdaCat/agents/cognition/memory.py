from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Generic, TypeVar

S = TypeVar("S")  # State type


@dataclass(frozen=True)
class AgentState(Generic[S]):
    """Persistent agent state with memory and beliefs.
    
    This is the core state structure that agents maintain across
    interactions, supporting both explicit memory and weighted beliefs.
    """

    data: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    beliefs: Dict[str, float] = field(default_factory=dict)
    scratch: Dict[str, Any] = field(default_factory=dict)

    def remember(self, key: str, value: Any) -> AgentState[S]:
        """Add a memory entry."""
        new_memory = dict(self.memory)
        new_memory[key] = value
        return AgentState(
            data=self.data,
            memory=new_memory,
            beliefs=self.beliefs,
            scratch=self.scratch
        )

    def recall(self, key: str, default: Any = None) -> Any:
        """Recall a memory entry."""
        return self.memory.get(key, default)

    def update_belief(self, proposition: str, delta_logit: float) -> AgentState[S]:
        """Update belief in a proposition using log-odds.
        
        Args:
            proposition: The proposition to update belief for
            delta_logit: Change in log-odds (positive = more likely, negative = less likely)
        """
        new_beliefs = dict(self.beliefs)
        current_logit = new_beliefs.get(proposition, 0.0)
        new_beliefs[proposition] = current_logit + delta_logit
        return AgentState(
            data=self.data,
            memory=self.memory,
            beliefs=new_beliefs,
            scratch=self.scratch
        )

    def get_belief(self, proposition: str) -> float:
        """Get current belief strength as log-odds."""
        return self.beliefs.get(proposition, 0.0)

    def get_belief_probability(self, proposition: str) -> float:
        """Get current belief as probability (0.0 to 1.0)."""
        import math
        logit = self.get_belief(proposition)
        return 1.0 / (1.0 + math.exp(-logit))

    def set_scratch(self, key: str, value: Any) -> AgentState[S]:
        """Set a scratch variable (temporary state)."""
        new_scratch = dict(self.scratch)
        new_scratch[key] = value
        return AgentState(
            data=self.data,
            memory=self.memory,
            beliefs=self.beliefs,
            scratch=new_scratch
        )

    def get_scratch(self, key: str, default: Any = None) -> Any:
        """Get a scratch variable."""
        return self.scratch.get(key, default)

    def clear_scratch(self) -> AgentState[S]:
        """Clear all scratch variables."""
        return AgentState(
            data=self.data,
            memory=self.memory,
            beliefs=self.beliefs,
            scratch={}
        )

    def update_data(self, updates: Dict[str, Any]) -> AgentState[S]:
        """Update the main data section."""
        new_data = dict(self.data)
        new_data.update(updates)
        return AgentState(
            data=new_data,
            memory=self.memory,
            beliefs=self.beliefs,
            scratch=self.scratch
        )

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get a data entry."""
        return self.data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "data": self.data,
            "memory": self.memory,
            "beliefs": self.beliefs,
            "scratch": self.scratch
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentState[S]:
        """Create from dictionary."""
        return cls(
            data=data.get("data", {}),
            memory=data.get("memory", {}),
            beliefs=data.get("beliefs", {}),
            scratch=data.get("scratch", {})
        )


# Belief update functions
def bayesian_update(
    prior_logit: float,
    evidence_logit: float
) -> float:
    """Bayesian belief update in log-odds space.
    
    Args:
        prior_logit: Prior belief as log-odds
        evidence_logit: Evidence strength as log-odds
        
    Returns:
        Updated belief as log-odds
    """
    return prior_logit + evidence_logit


def decay_beliefs(
    beliefs: Dict[str, float],
    decay_factor: float = 0.95
) -> Dict[str, float]:
    """Apply exponential decay to beliefs.
    
    Args:
        beliefs: Current beliefs as log-odds
        decay_factor: Decay factor (0.0 to 1.0, closer to 0 = more decay)
        
    Returns:
        Decayed beliefs
    """
    return {prop: logit * decay_factor for prop, logit in beliefs.items()}


def normalize_beliefs(
    beliefs: Dict[str, float],
    max_logit: float = 10.0
) -> Dict[str, float]:
    """Normalize beliefs to prevent extreme values.
    
    Args:
        beliefs: Current beliefs as log-odds
        max_logit: Maximum allowed log-odds value
        
    Returns:
        Normalized beliefs
    """
    return {
        prop: max(-max_logit, min(max_logit, logit))
        for prop, logit in beliefs.items()
    }


# Memory management functions
def consolidate_memory(
    memory: Dict[str, Any],
    max_entries: int = 1000
) -> Dict[str, Any]:
    """Consolidate memory by removing oldest entries if needed.
    
    Args:
        memory: Current memory
        max_entries: Maximum number of entries to keep
        
    Returns:
        Consolidated memory
    """
    if len(memory) <= max_entries:
        return memory

    # Simple strategy: keep the most recent entries
    # In a real system, you might want more sophisticated consolidation
    items = list(memory.items())
    return dict(items[-max_entries:])


def merge_memories(
    memory1: Dict[str, Any],
    memory2: Dict[str, Any],
    strategy: str = "left_biased"
) -> Dict[str, Any]:
    """Merge two memories using the specified strategy.
    
    Args:
        memory1: First memory
        memory2: Second memory
        strategy: Merge strategy ("left_biased", "right_biased", "timestamp_based")
        
    Returns:
        Merged memory
    """
    if strategy == "left_biased":
        result = dict(memory2)
        result.update(memory1)
        return result
    elif strategy == "right_biased":
        result = dict(memory1)
        result.update(memory2)
        return result
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")


# State lenses for focused access
def memory_lens() -> Any:  # Lens[AgentState, Dict[str, Any]]
    """Lens for accessing the memory section."""
    from ..actions import lens

    def get_memory(state: AgentState[S]) -> Dict[str, Any]:
        return state.memory

    def set_memory(state: AgentState[S], new_memory: Dict[str, Any]) -> AgentState[S]:
        return AgentState(
            data=state.data,
            memory=new_memory,
            beliefs=state.beliefs,
            scratch=state.scratch
        )

    return lens(get_memory, set_memory)


def beliefs_lens() -> Any:  # Lens[AgentState, Dict[str, float]]
    """Lens for accessing the beliefs section."""
    from ..actions import lens

    def get_beliefs(state: AgentState[S]) -> Dict[str, float]:
        return state.beliefs

    def set_beliefs(state: AgentState[S], new_beliefs: Dict[str, float]) -> AgentState[S]:
        return AgentState(
            data=state.data,
            memory=state.memory,
            beliefs=new_beliefs,
            scratch=state.scratch
        )

    return lens(get_beliefs, set_beliefs)


def data_lens() -> Any:  # Lens[AgentState, Dict[str, Any]]
    """Lens for accessing the data section."""
    from ..actions import lens

    def get_data(state: AgentState[S]) -> Dict[str, Any]:
        return state.data

    def set_data(state: AgentState[S], new_data: Dict[str, Any]) -> AgentState[S]:
        return AgentState(
            data=new_data,
            memory=state.memory,
            beliefs=state.beliefs,
            scratch=state.scratch
        )

    return lens(get_data, set_data)
