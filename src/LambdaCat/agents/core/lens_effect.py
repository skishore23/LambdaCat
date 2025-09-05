from __future__ import annotations

from typing import Any, Callable, TypeVar

from ..actions import Lens
from .effect import Effect, with_trace

S = TypeVar("S")  # State
A = TypeVar("A")  # Sub-state
B = TypeVar("B")  # Sub-state


def with_lens(effect: Effect[A, A], lens: Lens[S, A]) -> Effect[S, S]:
    """Apply a lens to an effect for focused state manipulation.

    This is the functorial mapping of lenses over effects:
    Lens[S, A] -> Effect[A, A] -> Effect[S, S]

    Laws:
    - get-put: lens.get(lens.set(a, s)) = a
    - put-get: lens.set(lens.get(s), s) = s
    - put-put: lens.set(a2, lens.set(a1, s)) = lens.set(a2, s)
    """

    async def lens_effect(s: S, ctx: dict[str, Any]) -> tuple[S, list[dict[str, Any]], Any]:
        # Extract sub-state using lens
        sub_state = lens.get(s)

        # Run effect on sub-state
        sub_result, trace, result = await effect.run(sub_state, ctx)

        if isinstance(result, dict) and result.get("error"):
            return (s, trace, result)

        # Update main state with new sub-state
        new_state = lens.set(s, sub_result)
        return (new_state, trace, {"success": True, "result": new_state})

    return with_trace("lens_focus", Effect(lens_effect))


def compose_lens_effects(
    outer_lens: Lens[S, A],
    inner_lens: Lens[A, B],
    effect: Effect[B, B]
) -> Effect[S, S]:
    """Compose lens effects: outer_lens . inner_lens . effect.

    This preserves lens composition laws:
    (f . g) . h = f . (g . h)
    """
    # Compose lenses
    composed_lens = Lens(
        get=lambda s: inner_lens.get(outer_lens.get(s)),
        set=lambda s, b: outer_lens.set(
            outer_lens.get(s),
            inner_lens.set(outer_lens.get(s), b)
        )
    )

    return with_lens(effect, composed_lens)


def lens_map(f: Callable[[A], B], lens: Lens[S, A]) -> Effect[S, S]:
    """Map a function over a lens focus.

    This creates an effect that applies f to the focused sub-state.
    """

    async def map_effect(s: S, ctx: dict[str, Any]) -> tuple[S, list[dict[str, Any]], Any]:
        sub_state = lens.get(s)
        new_sub_state = f(sub_state)
        new_state = lens.set(s, new_sub_state)

        return (new_state, [{"span": "lens_map"}], {"success": True, "result": new_state})

    return with_trace("lens_map", Effect(map_effect))


def lens_modify(f: Callable[[A], A], lens: Lens[S, A]) -> Effect[S, S]:
    """Modify a lens focus with a function.

    This creates an effect that modifies the focused sub-state.
    """

    async def modify_effect(s: S, ctx: dict[str, Any]) -> tuple[S, list[dict[str, Any]], Any]:
        sub_state = lens.get(s)
        new_sub_state = f(sub_state)
        new_state = lens.set(s, new_sub_state)

        return (new_state, [{"span": "lens_modify"}], {"success": True, "result": new_state})

    return with_trace("lens_modify", Effect(modify_effect))


def lens_gets(f: Callable[[A], B], lens: Lens[S, A]) -> Effect[S, B]:
    """Get a value from a lens focus.

    This creates an effect that extracts a value from the focused sub-state.
    """

    async def gets_effect(s: S, ctx: dict[str, Any]) -> tuple[S, list[dict[str, Any]], Any]:
        sub_state = lens.get(s)
        value = f(sub_state)

        return (s, [{"span": "lens_gets"}], {"success": True, "result": value})

    return with_trace("lens_gets", Effect(gets_effect))


def lens_put(value: A, lens: Lens[S, A]) -> Effect[S, S]:
    """Put a value into a lens focus.

    This creates an effect that sets the focused sub-state to a value.
    """

    async def put_effect(s: S, ctx: dict[str, Any]) -> tuple[S, list[dict[str, Any]], Any]:
        new_state = lens.set(s, value)

        return (new_state, [{"span": "lens_put"}], {"success": True, "result": new_state})

    return with_trace("lens_put", Effect(put_effect))


# Lens composition utilities
def compose_lenses(outer: Lens[S, A], inner: Lens[A, B]) -> Lens[S, B]:
    """Compose two lenses: outer . inner.

    This preserves lens composition laws.
    """
    return Lens(
        get=lambda s: inner.get(outer.get(s)),
        set=lambda s, b: outer.set(
            s,
            inner.set(outer.get(s), b)
        )
    )


def identity_lens() -> Lens[S, S]:
    """Identity lens: get(s) = s, set(s, s') = s'."""
    return Lens(
        get=lambda s: s,
        set=lambda s, s_new: s_new
    )


def const_lens(value: A) -> Lens[S, A]:
    """Constant lens: get(s) = value, set(s, a) = s."""
    return Lens(
        get=lambda s: value,
        set=lambda s, a: s
    )


# Lens laws verification
class LensLaws:
    """Verify lens laws for correctness."""

    @staticmethod
    def verify_get_put(lens: Lens[S, A], s: S, a: A) -> bool:
        """Verify get-put law: lens.get(lens.set(a, s)) = a"""
        try:
            result = lens.get(lens.set(s, a))
            return result == a
        except Exception:
            return False

    @staticmethod
    def verify_put_get(lens: Lens[S, A], s: S) -> bool:
        """Verify put-get law: lens.set(lens.get(s), s) = s"""
        try:
            result = lens.set(s, lens.get(s))
            return result == s
        except Exception:
            return False

    @staticmethod
    def verify_put_put(lens: Lens[S, A], s: S, a1: A, a2: A) -> bool:
        """Verify put-put law: lens.set(a2, lens.set(a1, s)) = lens.set(a2, s)"""
        try:
            # First put a1, then put a2
            intermediate = lens.set(s, a1)
            result1 = lens.set(intermediate, a2)
            # Direct put a2
            result2 = lens.set(s, a2)
            return result1 == result2
        except Exception:
            return False

    @staticmethod
    def verify_all_laws(lens: Lens[S, A], s: S, a1: A, a2: A) -> bool:
        """Verify all lens laws."""
        return (
            LensLaws.verify_get_put(lens, s, a1) and
            LensLaws.verify_put_get(lens, s) and
            LensLaws.verify_put_put(lens, s, a1, a2)
        )


# Common lens patterns
def dict_lens(key: str) -> Lens[dict[str, Any], Any]:
    """Lens for dictionary access."""
    return Lens(
        get=lambda d: d.get(key),
        set=lambda d, value: {**d, key: value}
    )


def list_lens(index: int) -> Lens[list[Any], Any]:
    """Lens for list access."""
    return Lens(
        get=lambda lst: lst[index] if index < len(lst) else None,
        set=lambda lst, value: [value if i == index else lst[i] for i in range(len(lst))]
    )


def nested_dict_lens(*keys: str) -> Lens[dict[str, Any], Any]:
    """Lens for nested dictionary access."""
    def get_nested(d: dict[str, Any]) -> Any:
        current = d
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def set_nested(d: dict[str, Any], value: Any) -> dict[str, Any]:
        result = dict(d)
        current = result
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        return result

    return Lens(get=get_nested, set=set_nested)


# Effect composition with lenses
def focus_effect(
    lens: Lens[S, A],
    effect: Effect[A, A]
) -> Effect[S, S]:
    """Focus an effect on a sub-state using a lens.

    This is the main composition operator for lens + effect.
    """
    return with_lens(effect, lens)


def focus_sequence(
    lens: Lens[S, A],
    *effects: Effect[A, A]
) -> Effect[S, S]:
    """Focus a sequence of effects on a sub-state."""
    if not effects:
        return Effect.pure(lambda s: s)

    # Compose effects sequentially
    composed = effects[0]
    for effect in effects[1:]:
        composed = composed.bind(lambda _, eff=effect: eff)

    return focus_effect(lens, composed)


def focus_parallel(
    lens: Lens[S, A],
    *effects: Effect[A, A],
    merge_state: Callable[[A, A], A] = lambda a1, a2: a2
) -> Effect[S, S]:
    """Focus parallel effects on a sub-state."""
    if not effects:
        from ..effect import Effect
        return Effect.pure(lambda s: s)

    # Compose effects in parallel
    from .effect import Effect
    parallel_effect = Effect.par_mapN(merge_state, *effects)

    return focus_effect(lens, parallel_effect)
