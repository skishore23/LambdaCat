from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Mapping
from inspect import signature
from typing import Callable, Generic, Protocol, TypeVar

from ..core.fp.kleisli import Kleisli
from ..core.fp.typeclasses import MonadT
from ..core.presentation import Formal1
from .actions import Plan
from .core.compile_async import ActionRegistry, AsyncCompiler, ParallelSpec

State = TypeVar("State")
Ctx = TypeVar("Ctx")
TState = TypeVar("TState")
T = TypeVar("T")


class Action(Protocol, Generic[State, Ctx]):
    """Action protocol - can be sync or async."""
    def __call__(self, x: State, ctx: Ctx | None = None) -> State | Awaitable[State]: ...


async def _maybe_await(x: State | Awaitable[State]) -> State:
    """Await if coroutine, otherwise return as-is."""
    return await x if asyncio.iscoroutine(x) else x


async def call_action(fn: Action[State, Ctx], s: State, ctx: Ctx | None) -> State:
    """Call an action (sync or async) and return the result."""
    res = fn(s, ctx)
    return await _maybe_await(res)


def sequential_functor(
    implementation: Mapping[str, Action[State, Ctx]],
    mode: str = "sequential",
) -> Callable[[Formal1], Callable[[State, Ctx | None], Awaitable[State]]]:
    """Create a sequential functor for async execution."""
    if mode != "sequential":
        raise ValueError("Only sequential mode is supported")

    def F(plan: Formal1) -> Callable[[State, Ctx | None], Awaitable[State]]:
        async def run(x: State, ctx: Ctx | None = None) -> State:
            value = x
            for step in plan.factors:
                fn = implementation[step]
                value = await call_action(fn, value, ctx)
            return value
        return run

    return F


def compile_to_kleisli(
    implementation: Mapping[str, Action[State, Ctx]],
    plan: Plan[State, Ctx],
    monad_cls: type[MonadT[object]],
    mode: str = "monadic"
) -> Kleisli[MonadT[object], State, State]:
    """Compile a plan to a Kleisli arrow for the given monad.

    This compiles the plan using the async runtime and converts the result
    to a Kleisli arrow that can be used with the specified monad.
    """
    if mode not in ("monadic", "applicative"):
        raise ValueError("mode must be 'monadic' or 'applicative'")

    # Convert to ActionRegistry format
    actions: ActionRegistry[State] = {}
    for name, action in implementation.items():
        actions[name] = action

    # Use AsyncCompiler to get the Effect
    compiler = AsyncCompiler(actions)
    effect = compiler.compile(plan)

    def kleisli_run(s: State) -> MonadT[object]:
        """Convert async Effect to Kleisli arrow."""
        # Run the effect synchronously and wrap result in the monad
        try:
            import asyncio
            final_state, _, result = asyncio.run(effect.run(s, {}))

            # Check if result is an error
            if hasattr(result, 'error'):
                # Return empty monad for errors
                return monad_cls.empty() if hasattr(monad_cls, 'empty') else monad_cls.pure(s)

            # Return the final state wrapped in the monad
            return monad_cls.pure(final_state)
        except Exception:
            # Return empty monad for exceptions
            return monad_cls.empty() if hasattr(monad_cls, 'empty') else monad_cls.pure(s)

    return Kleisli(kleisli_run)


def compile_plan(
    implementation: Mapping[str, Action[State, Ctx]],
    plan: Plan[State, Ctx],
    *,
    choose_fn: Callable[[list[object]], int] | None = None,
    aggregate_fn: Callable[[list[object]], object] | None = None,
    parallel_spec: ParallelSpec | None = None,
) -> Callable[[State, Ctx | None], Awaitable[State]]:
    """Compile a plan to an async executable function.

    This is the main entry point for plan compilation.
    """
    # Convert to ActionRegistry format
    actions: ActionRegistry[State] = {}
    for name, action in implementation.items():
        actions[name] = action

    # Use AsyncCompiler with parallel spec
    compiler = AsyncCompiler(actions, default_parallel_spec=parallel_spec)
    effect = compiler.compile(plan)

    async def run_async(x: State, ctx: Ctx | None = None) -> State:
        final_state, _, result = await effect.run(x, ctx or {})
        if hasattr(result, 'error'):
            raise RuntimeError(f"Plan execution failed: {result.error}")
        return final_state

    return run_async


# Re-export helper for agents (generic)
def call_action_sync(fn: Callable[..., TState], x: TState, ctx: Ctx | None) -> TState:
    """Call a sync action - for backward compatibility with existing code."""
    return _call_action_generic(fn, x, ctx)


def _call_action_generic(fn: Callable[..., TState], x: TState, ctx: Ctx | None) -> TState:
    """Generic action caller for sync functions."""
    sig = signature(fn)
    params = list(sig.parameters.values())
    # Accept exactly 1 or 2 parameters; anything else is an error
    if len(params) == 1:
        return fn(x)
    if len(params) == 2:
        return fn(x, ctx)
    raise TypeError("Action must accept 1 (x) or 2 (x, ctx) parameters")


# Structured plan interpreter (Seq / Par / Choose / Focus / LoopWhile)
ChooseFn = Callable[[list[object]], int]
AggregateFn = Callable[[list[object]], object]


# -------------------------- Helpers for Par/Choose --------------------------


def concat(sep: str = "") -> Callable[[list[str]], str]:
    """Concatenate strings with separator."""
    def _agg(outputs: list[str]) -> str:
        if not outputs:
            return "" if sep == "" else sep.join([])
        return sep.join(outputs)
    return _agg


def first() -> Callable[[list[T]], int]:
    """Choose first item."""
    def _choose(outputs: list[T]) -> int:
        if not outputs:
            raise AssertionError("choose on empty outputs")
        return 0
    return _choose


def argmax(by: Callable[[T], float]) -> Callable[[list[T]], int]:
    """Choose item with maximum score."""
    def _choose(outputs: list[T]) -> int:
        if not outputs:
            raise AssertionError("choose on empty outputs")
        scores = [by(o) for o in outputs]
        best = max(range(len(scores)), key=lambda i: scores[i])
        return best
    return _choose

