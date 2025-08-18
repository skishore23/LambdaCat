from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterable, List, Mapping, Sequence, Tuple, TypeVar

from .actions import Plan
from .runtime import strong_monoidal_functor, call_action, compile_structured_plan
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
    runner = compile_structured_plan(implementation, plan, choose_fn=choose_fn, aggregate_fn=aggregate_fn)
    t0 = _now_ms()
    try:
        output = runner(input_value, ctx)
        ok = True
    except Exception:
        ok = False
        raise
    finally:
        duration = _now_ms() - t0
    step_name = type(plan).__name__
    trace: List[StepTrace[State]] = [
        StepTrace(step_name, ok, duration, input_value if snapshot else None, output if snapshot else None)
    ]
    return RunReport(output=output, score=None, trace=tuple(trace))


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

