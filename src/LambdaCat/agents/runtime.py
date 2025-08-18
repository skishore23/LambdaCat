from typing import Callable, Dict, Generic, List, Mapping, Protocol, Sequence, Tuple, TypeVar
from LambdaCat.core.fp.kleisli import Kleisli
from LambdaCat.core.fp.typeclasses import MonadT
from inspect import signature
from ..core.presentation import Formal1
from .actions import Task, Sequence as SeqNode, Parallel, Choose, Focus, LoopWhile, Plan


State = TypeVar("State")
Ctx = TypeVar("Ctx")
TState = TypeVar("TState")
T = TypeVar("T")


class Action(Protocol, Generic[State, Ctx]):
    def __call__(self, x: State, ctx: Ctx | None = None) -> State: ...


def _call_action_generic(fn: Callable[..., TState], x: TState, ctx: Ctx | None) -> TState:
    sig = signature(fn)
    params = list(sig.parameters.values())
    # Accept exactly 1 or 2 parameters; anything else is an error
    if len(params) == 1:
        return fn(x)
    if len(params) == 2:
        return fn(x, ctx)
    raise TypeError("Action must accept 1 (x) or 2 (x, ctx) parameters")


def strong_monoidal_functor(
    implementation: Mapping[str, Action[State, Ctx]],
    mode: str = "sequential",
):
    if mode != "sequential":
        raise ValueError("Only sequential mode is supported")

    def F(plan: Formal1):
        def run(x: State, ctx: Ctx | None = None) -> State:
            value = x
            for step in plan.factors:
                fn = implementation[step]
                value = _call_action_generic(fn, value, ctx)
            return value
        return run

    return F

# Re-export helper for agents (generic)
def call_action(fn: Callable[..., TState], x: TState, ctx: Ctx | None) -> TState:
    return _call_action_generic(fn, x, ctx)


# Structured plan interpreter (Seq / Par / Choose / Focus / LoopWhile)
ChooseFn = Callable[[List[State]], int]
AggregateFn = Callable[[List[State]], State]


# -------------------------- Helpers for Par/Choose --------------------------


def concat(sep: str = "") -> Callable[[List[str]], str]:
    def _agg(outputs: List[str]) -> str:
        # Fail-fast: ensure homogeneous, string-like types; otherwise raise
        if not outputs:
            return "" if sep == "" else sep.join([])
        return sep.join(outputs)
    return _agg


def first() -> Callable[[List[T]], int]:
    def _choose(outputs: List[T]) -> int:
        if not outputs:
            raise AssertionError("choose on empty outputs")
        return 0
    return _choose


def argmax(by: Callable[[T], float]) -> Callable[[List[T]], int]:
    def _choose(outputs: List[T]) -> int:
        if not outputs:
            raise AssertionError("choose on empty outputs")
        scores = [by(o) for o in outputs]
        best = max(range(len(scores)), key=lambda i: scores[i])
        return best
    return _choose


def _compile_plan(
    implementation: Mapping[str, Action[State, Ctx]],
    plan: Plan[State, Ctx],
    *,
    choose_fn: ChooseFn | None,
    aggregate_fn: AggregateFn | None,
):
    if isinstance(plan, Task):
        fn = implementation[plan.name]

        def run_atom(x: State, ctx: Ctx | None = None) -> State:
            return _call_action_generic(fn, x, ctx)

        return run_atom

    if isinstance(plan, SeqNode):
        runners: Tuple[Callable[[State, Ctx | None], State], ...] = tuple(
            _compile_plan(implementation, p, choose_fn=choose_fn, aggregate_fn=aggregate_fn) for p in plan.items
        )

        def run_seq(x: State, ctx: Ctx | None = None) -> State:
            value = x
            for r in runners:
                value = r(value, ctx)
            return value

        return run_seq

    if isinstance(plan, Parallel):
        if aggregate_fn is None:
            raise AssertionError("Parallel requires an aggregate_fn to combine branch outputs")
        runners: Tuple[Callable[[State, Ctx | None], State], ...] = tuple(
            _compile_plan(implementation, p, choose_fn=choose_fn, aggregate_fn=aggregate_fn) for p in plan.items
        )

        def run_par(x: State, ctx: Ctx | None = None) -> State:
            outputs: List[State] = [r(x, ctx) for r in runners]
            return aggregate_fn(outputs)

        return run_par

    if isinstance(plan, Choose):
        if choose_fn is None:
            raise AssertionError("Choose requires a choose_fn to select a branch")
        runners: Tuple[Callable[[State, Ctx | None], State], ...] = tuple(
            _compile_plan(implementation, p, choose_fn=choose_fn, aggregate_fn=aggregate_fn) for p in plan.items
        )

        def run_choose(x: State, ctx: Ctx | None = None) -> State:
            outputs: List[State] = [r(x, ctx) for r in runners]
            idx = choose_fn(outputs)
            if not (0 <= idx < len(outputs)):
                raise AssertionError("choose_fn returned invalid index")
            return outputs[idx]

        return run_choose

    if isinstance(plan, Focus):
        inner_runner = _compile_plan(implementation, plan.inner, choose_fn=choose_fn, aggregate_fn=aggregate_fn)

        def run_focus(x: State, ctx: Ctx | None = None) -> State:
            sub_value = plan.lens.get(x)
            new_sub = inner_runner(sub_value, ctx)
            return plan.lens.set(x, new_sub)

        return run_focus

    if isinstance(plan, LoopWhile):
        body_runner = _compile_plan(implementation, plan.body, choose_fn=choose_fn, aggregate_fn=aggregate_fn)

        def run_loop(x: State, ctx: Ctx | None = None) -> State:
            value = x
            while plan.predicate(value):
                value = body_runner(value, ctx)
            return value

        return run_loop

    raise TypeError("Unknown Plan node")


def compile_structured_plan(
    implementation: Mapping[str, Action[State, Ctx]],
    plan: Plan[State, Ctx],
    *,
    choose_fn: ChooseFn | None = None,
    aggregate_fn: AggregateFn | None = None,
):
    return _compile_plan(implementation, plan, choose_fn=choose_fn, aggregate_fn=aggregate_fn)


S = TypeVar("S")


def compile_plan_kleisli(
    implementation: Mapping[str, Action[S, Ctx]],
    plan: Sequence[str],
    *,
    monad_pure: Callable[[S], MonadT[S]],
    ctx: Ctx | None = None,
) -> Kleisli[S, S]:
    """Compile a sequential plan of action names into a Kleisli arrow over a monad.

    - `implementation`: mapping from action name to `(state, ctx?) -> state`
    - `monad_pure`: constructor for `State -> M State`
    - `plan`: sequence of action names; evaluated left-to-right via monadic bind

    This compiler is sequential-only; other modes are intentionally unsupported (fail-fast elsewhere).
    """

    def lift_action(name: str) -> Kleisli[S, S]:
        if name not in implementation:
            raise KeyError(f"Unknown action: {name}")
        fn = implementation[name]
        return Kleisli(lambda s: monad_pure(_call_action_generic(fn, s, ctx)))

    if not plan:
        return Kleisli(lambda s: monad_pure(s))

    acc = lift_action(plan[0])
    for step in plan[1:]:
        acc = acc.then(lift_action(step))
    return acc

