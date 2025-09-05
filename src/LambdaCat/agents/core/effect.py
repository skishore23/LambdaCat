from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar, Union

# from ..core.fp.typeclasses import MonadT  # Not needed for Effect implementation

S = TypeVar("S")  # State
A = TypeVar("A")  # Value
B = TypeVar("B")  # Value
E = TypeVar("E")  # Error

# Trace is a list of span dictionaries for observability
Trace = list[dict[str, Any]]

# Result type for Effect
@dataclass(frozen=True)
class Ok(Generic[A]):
    value: A

    def __repr__(self) -> str:
        return f"Ok({self.value})"


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def __repr__(self) -> str:
        return f"Err({self.error})"


Result = Union[Ok[A], Err]

# The core Effect monad: (S, Ctx) -> await (S, Trace, Result[A])
EffectFn = Callable[[S, dict[str, Any]], Awaitable[tuple[S, Trace, Result[A]]]]


@dataclass(frozen=True)
class Effect(Generic[S, A]):
    """The core Effect monad for async, stateful, traced computations.
    
    Effect[S, A] represents a computation that:
    - Takes state S and context dict
    - Returns (new_state, trace, result)
    - Is async and can be composed with other Effects
    - Supports true parallelism via Applicative operations
    """

    run: EffectFn[S, A]

    @classmethod
    def pure(cls, value: A) -> Effect[S, A]:
        """Pure value lifted into Effect."""
        async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[A]]:
            return (s, [], Ok(value))
        return cls(go)

    def map(self, f: Callable[[A], B]) -> Effect[S, B]:
        """Functor map: fmap f (Effect g) = Effect (f . g)"""
        async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[B]]:
            s2, tr, r = await self.run(s, ctx)
            if isinstance(r, Ok):
                return (s2, tr, Ok(f(r.value)))
            else:
                return (s2, tr, r)  # type: ignore[return-value]
        return Effect(go)

    def bind(self, f: Callable[[A], Effect[S, B]]) -> Effect[S, B]:
        """Monadic bind: (>>=)"""
        async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[B]]:
            s1, tr1, r1 = await self.run(s, ctx)
            if isinstance(r1, Err):
                return (s1, tr1, r1)  # type: ignore[return-value]

            # Continue with the next effect
            if isinstance(r1, Ok):
                effect2 = f(r1.value)
            else:
                # This should not happen since we checked for Err above
                return (s1, tr1, r1)
            s2, tr2, r2 = await effect2.run(s1, ctx)
            return (s2, tr1 + tr2, r2)
        return Effect(go)

    def ap(self: Effect[S, Callable[[A], B]], other: Effect[S, A]) -> Effect[S, B]:
        """Applicative apply: (<*>)"""
        async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[B]]:
            # Run both effects in parallel
            s1, tr1, r1 = await self.run(s, ctx)
            s2, tr2, r2 = await other.run(s, ctx)

            # Combine traces
            combined_trace = tr1 + tr2

            # Check for errors
            if isinstance(r1, Err):
                return (s1, combined_trace, r1)  # type: ignore[return-value]
            if isinstance(r2, Err):
                return (s2, combined_trace, r2)  # type: ignore[return-value]

            # Apply function to value
            return (s2, combined_trace, Ok(r1.value(r2.value)))
        return Effect(go)

    @staticmethod
    def par_mapN(
        merge_state: Callable[[S, S], S],
        *effects: Effect[S, Any]
    ) -> Effect[S, tuple[Any, ...]]:
        """Parallel composition of N effects using Applicative.
        
        This is the key operation for true parallelism - all effects run
        concurrently and their results are combined.
        """
        async def go(s0: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[tuple[Any, ...]]]:
            # Run all effects in parallel
            async def run_effect(effect: Effect[S, Any]) -> tuple[S, Trace, Result[Any]]:
                return await effect.run(s0, ctx)

            # Use asyncio.gather for true parallelism
            results = await asyncio.gather(*[run_effect(e) for e in effects])

            # Extract states, traces, and results
            states, traces, results_list = zip(*results)

            # Merge all states using the provided merge function
            final_state = merge_all_states(merge_state, states, s0)

            # Combine all traces
            combined_trace = [span for trace in traces for span in trace]

            # Check for any errors
            if any(isinstance(r, Err) for r in results_list):
                first_error = next(r for r in results_list if isinstance(r, Err))
                return (final_state, combined_trace, first_error)  # type: ignore[return-value]

            # All succeeded - combine values
            values = tuple(r.value for r in results_list if isinstance(r, Ok))
            return (final_state, combined_trace, Ok(values))

        return Effect(go)

    @staticmethod
    def race_first(*effects: Effect[S, A]) -> Effect[S, A]:
        """Race effects and return the first one to complete (Alt/Alternative)."""
        async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[A]]:
            # Create tasks for all effects
            tasks = [asyncio.create_task(effect.run(s, ctx)) for effect in effects]

            try:
                # Wait for first completion
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                # Cancel remaining tasks
                for task in pending:
                    task.cancel()

                # Get the first result
                first_task = next(iter(done))
                return await first_task

            except Exception as e:
                # Cancel all tasks on error
                for task in tasks:
                    task.cancel()
                return (s, [{"span": "race_error", "error": str(e)}], Err(e))

        return Effect(go)

    @staticmethod
    def timeout(timeout_seconds: float, effect: Effect[S, A]) -> Effect[S, A]:
        """Add timeout to an effect."""
        async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[A]]:
            try:
                return await asyncio.wait_for(effect.run(s, ctx), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                return (s, [{"span": "timeout", "seconds": timeout_seconds}], Err("timeout"))

        return Effect(go)

    async def __call__(self, s: S, ctx: dict[str, Any] | None = None) -> tuple[S, Trace, Result[A]]:
        """Run the effect with given state and context."""
        return await self.run(s, ctx or {})


def merge_all_states(merge: Callable[[S, S], S], states: tuple[S, ...], initial: S) -> S:
    """Merge multiple states using the provided merge function."""
    result = initial
    for state in states:
        result = merge(result, state)
    return result


# Helper functions for common patterns
def lift_async(fn: Callable[[S, dict[str, Any]], Awaitable[A]]) -> Effect[S, A]:
    """Lift an async function to an Effect."""
    async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[A]]:
        try:
            result = await fn(s, ctx)
            return (s, [], Ok(result))
        except Exception as e:
            return (s, [{"span": "lift_error", "error": str(e)}], Err(e))
    return Effect(go)


def lift_sync(fn: Callable[[S, dict[str, Any]], A]) -> Effect[S, A]:
    """Lift a sync function to an Effect."""
    async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[A]]:
        try:
            result = fn(s, ctx)
            return (s, [], Ok(result))
        except Exception as e:
            return (s, [{"span": "lift_error", "error": str(e)}], Err(e))
    return Effect(go)


def with_trace(span_name: str, effect: Effect[S, A]) -> Effect[S, A]:
    """Add tracing to an effect."""
    async def go(s: S, ctx: dict[str, Any]) -> tuple[S, Trace, Result[A]]:
        import time
        start_time = time.perf_counter()

        s2, tr, r = await effect.run(s, ctx)

        duration = (time.perf_counter() - start_time) * 1000  # ms
        trace_entry = {"span": span_name, "duration_ms": round(duration, 2)}

        return (s2, tr + [trace_entry], r)

    return Effect(go)
