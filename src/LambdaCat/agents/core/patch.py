from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from ...core.fp.typeclasses import Monoid

S = TypeVar("S")  # State type


@dataclass(frozen=True)
class Patch(Generic[S]):
    """A monoidal patch for state updates.

    Patches represent small, composable changes to state that can be
    safely merged in parallel without conflicts.
    """

    updates: dict[str, Any]

    @classmethod
    def empty(cls) -> Patch[S]:
        """Identity element for the monoid."""
        return cls({})

    def combine(self, other: Patch[S]) -> Patch[S]:
        """Associative combination of patches.

        Left-biased merge: self takes precedence over other for conflicts.
        This ensures associativity: (a . b) . c = a . (b . c)
        """
        combined = dict(self.updates)
        combined.update(other.updates)
        return Patch(combined)

    def apply_to(self, state: S) -> S:
        """Apply this patch to a state."""
        if not isinstance(state, dict):
            raise TypeError("Patch can only be applied to dict-like states")

        result = dict(state)
        result.update(self.updates)
        return result  # type: ignore[return-value]


def patch_combine(s1: S, s2: S) -> S:
    """Default state combiner that merges dict states."""
    if not isinstance(s1, dict) or not isinstance(s2, dict):
        raise TypeError("patch_combine requires dict states")

    result = dict(s1)
    result.update(s2)
    return result  # type: ignore[return-value]


def create_patch_from_state(new_state: S) -> Patch[S]:
    """Create a patch that represents the entire new state."""
    if not isinstance(new_state, dict):
        raise TypeError("create_patch_from_state requires dict state")

    return Patch(dict(new_state))


def create_patch_updates(updates: dict[str, Any]) -> Patch[S]:
    """Create a patch with specific updates."""
    return Patch(updates)


# Lens-based patches for focused updates
def create_lens_patch(lens_path: str, value: Any) -> Patch[S]:
    """Create a patch for a specific lens path."""
    return Patch({lens_path: value})


# Monoid instance for patches
class PatchMonoid(Monoid[Patch[S]]):
    """Monoid instance for patches."""

    def empty(self) -> Patch[S]:
        return Patch.empty()

    def combine(self, left: Patch[S], right: Patch[S]) -> Patch[S]:
        return left.combine(right)


# Helper for creating state merge functions
def create_state_merger(merge_strategy: str = "left_biased") -> Callable[[S, S], S]:
    """Create a state merge function with the specified strategy."""
    if merge_strategy == "left_biased":
        return patch_combine
    elif merge_strategy == "right_biased":
        def right_biased_merge(s1: S, s2: S) -> S:
            if not isinstance(s1, dict) or not isinstance(s2, dict):
                raise TypeError("right_biased_merge requires dict states")
            result = dict(s2)
            result.update(s1)
            return result  # type: ignore[return-value]
        return right_biased_merge
    elif merge_strategy == "deep_merge":
        def deep_merge(s1: S, s2: S) -> S:
            if not isinstance(s1, dict) or not isinstance(s2, dict):
                raise TypeError("deep_merge requires dict states")

            result = dict(s1)
            for key, value in s2.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result  # type: ignore[return-value]
        return deep_merge
    else:
        raise ValueError(f"Unknown merge strategy: {merge_strategy}")


# Utility for extracting patches from state changes
def diff_states(old_state: S, new_state: S) -> Patch[S]:
    """Compute the patch that transforms old_state into new_state."""
    if not isinstance(old_state, dict) or not isinstance(new_state, dict):
        raise TypeError("diff_states requires dict states")

    updates = {}
    for key, value in new_state.items():
        if key not in old_state or old_state[key] != value:
            updates[key] = value

    return Patch(updates)
