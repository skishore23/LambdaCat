from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterable, List, Mapping, Sequence, Tuple, TypeVar

from .actions import Plan
from .runtime import call_action, compile_plan
from .runtime import Action
from ..core.presentation import Formal1


State = TypeVar("State")
Ctx = TypeVar("Ctx")
Score = Any


@dataclass(frozen=True)
class StepTrace(Generic[State]):
    name: str
    ok: bool
    duration_ms: float
    input_snapshot: State | None
    output_snapshot: State | None


@dataclass(frozen=True)
class RunReport(Generic[State]):
    output: State
    score: Score
    trace: Sequence[StepTrace[State]]


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


def run_plan(
    plan: Formal1,
    implementation: Mapping[str, Callable[..., State]],
    input_value: State,
    *,
    ctx: Ctx | None = None,
    evaluator: Callable[[State], Score] | None = None,
    snapshot: bool = False,
) -> RunReport[State]:
    value = input_value
    traces: List[StepTrace[State]] = []
    for step in plan.factors:
        fn = implementation[step]
        before = value if snapshot else None
        t0 = _now_ms()
        try:
            value = call_action(fn, value, ctx)
            ok = True
        except Exception:
            ok = False
            raise
        finally:
            duration = _now_ms() - t0
        after = value if snapshot else None
        traces.append(StepTrace(step, ok, duration, before, after))

    score: Score = evaluator(value) if evaluator is not None else None
    return RunReport(output=value, score=score, trace=tuple(traces))


def run_structured_plan(
    plan: Plan[State, Ctx],
    implementation: Mapping[str, Callable[..., State]],
    input_value: State,
    *,
    ctx: Ctx | None = None,
    choose_fn: Callable[[List[State]], int] | None = None,
    aggregate_fn: Callable[[List[State]], State] | None = None,
    snapshot: bool = False,
) -> RunReport[State]:
    # Per-task tracing by wrapping actions
    traces: List[StepTrace[State]] = []

    def _wrap(name: str, fn: Callable[..., State]) -> Action[State, Ctx]:
        def wrapped(x: State, c: Ctx | None = None) -> State:
            before = x if snapshot else None
            t0 = _now_ms()
            try:
                y = call_action(fn, x, c)
                ok_local = True
            except Exception:
                ok_local = False
                raise
            finally:
                duration = _now_ms() - t0
            after = y if snapshot else None
            traces.append(StepTrace(name, ok_local, duration, before, after))
            return y
        return wrapped

    traced_impl: Mapping[str, Action[State, Ctx]] = {k: _wrap(k, v) for k, v in implementation.items()}
    runner = compile_plan(traced_impl, plan, choose_fn=choose_fn, aggregate_fn=aggregate_fn)
    output = runner(input_value, ctx)
    return RunReport(output=output, score=None, trace=tuple(traces))


def choose_best(
    candidates: Sequence[Formal1],
    implementation: Mapping[str, Callable[..., State]],
    input_value: State,
    *,
    ctx: Ctx | None = None,
    evaluator: Callable[[State], Score],
    snapshot: bool = False,
) -> Tuple[Formal1, RunReport[State]]:
    best: Tuple[Formal1, RunReport[State]] | None = None
    for plan in candidates:
        report = run_plan(plan, implementation, input_value, ctx=ctx, evaluator=evaluator, snapshot=snapshot)
        if best is None or (report.score is not None and report.score > best[1].score):
            best = (plan, report)
    assert best is not None
    return best


def quick_functor_laws(
    implementation: Mapping[str, Callable[..., Any]],
    *,
    id_name: str | None = None,
    samples: Sequence[Any] = (),
    ctx: Any | None = None,
) -> None:
    # Check composition: running (f,g) equals applying f then g on samples
    names = list(implementation.keys())
    for f in names:
        for g in names:
            comp = Formal1((f, g))
            for x in samples:
                left = run_plan(comp, implementation, x, ctx=ctx).output
                right = call_action(implementation[g], call_action(implementation[f], x, ctx), ctx)
                if left != right:
                    raise AssertionError(f"Functor law failed: F({g}∘{f}) != F({g})∘F({f}) on {x}")
    # Identity if provided
    if id_name is not None:
        if id_name not in implementation:
            raise AssertionError(f"identity action '{id_name}' not in implementation")
        for x in samples:
            if run_plan(Formal1((id_name,)), implementation, x, ctx=ctx).output != x:
                raise AssertionError("Identity law failed: F(id)(x) != x")


@dataclass(frozen=True)
class Agent(Generic[State, Ctx]):
    implementation: Mapping[str, Callable[..., State]]
    evaluator: Callable[[State], Score] | None = None
    snapshot: bool = False

    def run(self, plan: Formal1, input_value: State, *, ctx: Ctx | None = None) -> RunReport[State]:
        return run_plan(plan, self.implementation, input_value, ctx=ctx, evaluator=self.evaluator, snapshot=self.snapshot)

    def choose_best(
        self,
        candidates: Sequence[Formal1],
        input_value: State,
        *,
        ctx: Ctx | None = None,
    ) -> Tuple[Formal1, RunReport[State]]:
        if self.evaluator is None:
            raise AssertionError("Agent.choose_best requires an evaluator")
        return choose_best(candidates, self.implementation, input_value, ctx=ctx, evaluator=self.evaluator, snapshot=self.snapshot)

    # -------------------------- Convenience helpers --------------------------

    def plan(self, *names: str) -> Formal1:
        return Formal1(tuple(names))

    def run_seq(self, *names: str, input_value: State, ctx: Ctx | None = None) -> RunReport[State]:
        return self.run(self.plan(*names), input_value, ctx=ctx)

    def run_structured(
        self,
        plan: "Plan[State, Ctx]",
        input_value: State,
        *,
        ctx: Ctx | None = None,
        choose_fn: Callable[[List[State]], int] | None = None,
        aggregate_fn: Callable[[List[State]], State] | None = None,
        snapshot: bool | None = None,
    ) -> RunReport[State]:
        snap = self.snapshot if snapshot is None else snapshot
        return run_structured_plan(
            plan,
            self.implementation,
            input_value,
            ctx=ctx,
            choose_fn=choose_fn,
            aggregate_fn=aggregate_fn,
            snapshot=snap,
        )


# ------------------------------ Agent Builder ------------------------------


class AgentBuilder(Generic[State, Ctx]):
    def __init__(self, implementation: Mapping[str, Callable[..., State]]):
        self._implementation = implementation
        self._evaluator: Callable[[State], Score] | None = None
        self._snapshot: bool = False

    def with_evaluator(self, evaluator: Callable[[State], Score]) -> "AgentBuilder[State, Ctx]":
        self._evaluator = evaluator
        return self

    def with_snapshot(self, snapshot: bool) -> "AgentBuilder[State, Ctx]":
        self._snapshot = snapshot
        return self

    def build(self) -> Agent[State, Ctx]:
        # Validate implementation signatures: accept (x) or (x, ctx)
        for name, fn in self._implementation.items():
            try:
                # Reuse call helper to validate arity using a dummy value is unsafe; instead inspect
                from inspect import signature

                params = list(signature(fn).parameters.values())
                if len(params) not in (1, 2):
                    raise TypeError
            except Exception:
                raise TypeError(f"Action '{name}' must accept 1 or 2 parameters (x) or (x, ctx)")
        return Agent(self._implementation, evaluator=self._evaluator, snapshot=self._snapshot)

