from collections.abc import Mapping
from inspect import signature
from typing import Callable, Generic, Protocol, TypeVar

from LambdaCat.core.fp.kleisli import Kleisli
from LambdaCat.core.fp.typeclasses import MonadT

from ..core.presentation import Formal1
from .actions import Choose, Focus, LoopWhile, Parallel, Plan, Task
from .actions import Sequence as SeqNode

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


def sequential_functor(
    implementation: Mapping[str, Action[State, Ctx]],
    mode: str = "sequential",
) -> Callable[[Formal1], Callable[[State, Ctx | None], State]]:
    if mode != "sequential":
        raise ValueError("Only sequential mode is supported")

    def F(plan: Formal1) -> Callable[[State, Ctx | None], State]:
        def run(x: State, ctx: Ctx | None = None) -> State:
            value = x
            for step in plan.factors:
                fn = implementation[step]
                value = _call_action_generic(fn, value, ctx)
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

    Note: Complex plans with parallel and choose operations may not work correctly
    in Kleisli context. For complex plans, use compile_plan instead.
    """
    if mode not in ("monadic", "applicative"):
        raise ValueError("mode must be 'monadic' or 'applicative'")

    def compile_rec(p: Plan[State, Ctx]) -> Kleisli[MonadT[object], State, State]:
        if isinstance(p, Task):
            # Convert action to Kleisli
            action = implementation[p.name]
            return Kleisli(lambda s: monad_cls.pure(action(s)))  # type: ignore[arg-type,return-value]

        elif isinstance(p, SeqNode):
            # Sequential composition
            if not p.items:
                return Kleisli.id(monad_cls)
            first = compile_rec(p.items[0])
            rest = compile_rec(SeqNode(p.items[1:])) if len(p.items) > 1 else Kleisli.id(monad_cls)
            return rest.compose(first)

        elif isinstance(p, Parallel):
            # Parallel operations are not supported in Kleisli compilation
            # Convert to sequential for compatibility
            if not p.items:
                return Kleisli.id(monad_cls)

            # Compile as sequential plan
            return compile_rec(SeqNode(p.items))

        elif isinstance(p, Choose):
            # Choose operations are not supported in Kleisli compilation
            # Convert to first item for compatibility
            if not p.items:
                raise ValueError("Choose with no items")

            return compile_rec(p.items[0])

        elif isinstance(p, Focus):
            # Focus on a sub-state
            inner = compile_rec(p.inner)
            return Kleisli(lambda s:  # type: ignore[arg-type,return-value]
                monad_cls.pure(p.lens.set(inner(p.lens.get(s)), s)))

        elif isinstance(p, LoopWhile):
            # Loop while predicate is true
            def loop_run(s: State) -> MonadT[object]:  # type: ignore[valid-type]
                current = s
                while p.predicate(current):
                    result = compile_rec(p.body)(current)
                    if isinstance(result, monad_cls):
                        # Extract from monad for loop condition
                        current = result.get_or_else(current) if hasattr(result, 'get_or_else') else current
                    else:
                        current = result
                return monad_cls.pure(current)  # type: ignore[assignment]

            return Kleisli(loop_run)

        else:
            raise TypeError(f"Unknown plan type: {type(p)}")

    return compile_rec(plan)


# Re-export helper for agents (generic)
def call_action(fn: Callable[..., TState], x: TState, ctx: Ctx | None) -> TState:
    return _call_action_generic(fn, x, ctx)


# Structured plan interpreter (Seq / Par / Choose / Focus / LoopWhile)
ChooseFn = Callable[[list[object]], int]
AggregateFn = Callable[[list[object]], object]


# -------------------------- Helpers for Par/Choose --------------------------


def concat(sep: str = "") -> Callable[[list[str]], str]:
    def _agg(outputs: list[str]) -> str:
        if not outputs:
            return "" if sep == "" else sep.join([])
        return sep.join(outputs)
    return _agg


def first() -> Callable[[list[T]], int]:
    def _choose(outputs: list[T]) -> int:
        if not outputs:
            raise AssertionError("choose on empty outputs")
        return 0
    return _choose


def argmax(by: Callable[[T], float]) -> Callable[[list[T]], int]:
    def _choose(outputs: list[T]) -> int:
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
) -> Callable[[State, Ctx | None], State]:
    if isinstance(plan, Task):
        fn = implementation[plan.name]

        def run_atom(x: State, ctx: Ctx | None = None) -> State:
            return _call_action_generic(fn, x, ctx)

        return run_atom

    elif isinstance(plan, SeqNode):
        items = [_compile_plan(implementation, item, choose_fn=choose_fn, aggregate_fn=aggregate_fn) for item in plan.items]

        def run_seq(x: State, ctx: Ctx | None = None) -> State:
            value = x
            for item in items:
                value = item(value, ctx)
            return value

        return run_seq

    elif isinstance(plan, Parallel):
        items = [_compile_plan(implementation, item, choose_fn=choose_fn, aggregate_fn=aggregate_fn) for item in plan.items]

        def run_par(x: State, ctx: Ctx | None = None) -> State:
            if not aggregate_fn:
                raise ValueError("Parallel execution requires aggregate_fn")
            outputs = [item(x, ctx) for item in items]
            return aggregate_fn(outputs)  # type: ignore[no-any-return]

        return run_par

    elif isinstance(plan, Choose):
        items = [_compile_plan(implementation, item, choose_fn=choose_fn, aggregate_fn=aggregate_fn) for item in plan.items]

        def run_choose(x: State, ctx: Ctx | None = None) -> State:
            if not choose_fn:
                raise ValueError("Choose execution requires choose_fn")
            outputs = [item(x, ctx) for item in items]
            choice_idx = choose_fn(outputs)
            return outputs[choice_idx]

        return run_choose

    elif isinstance(plan, Focus):
        inner = _compile_plan(implementation, plan.inner, choose_fn=choose_fn, aggregate_fn=aggregate_fn)

        def run_focus(x: State, ctx: Ctx | None = None) -> State:
            sub_state = plan.lens.get(x)
            new_sub_state = inner(sub_state, ctx)
            return plan.lens.set(x, new_sub_state)

        return run_focus

    elif isinstance(plan, LoopWhile):
        body = _compile_plan(implementation, plan.body, choose_fn=choose_fn, aggregate_fn=aggregate_fn)

        def run_loop(x: State, ctx: Ctx | None = None) -> State:
            current = x
            while plan.predicate(current):
                current = body(current, ctx)
            return current

        return run_loop

    else:
        raise TypeError(f"Unknown plan type: {type(plan)}")


def compile_plan(
    implementation: Mapping[str, Action[State, Ctx]],
    plan: Plan[State, Ctx],
    *,
    choose_fn: ChooseFn | None = None,
    aggregate_fn: AggregateFn | None = None,
) -> Callable[[State, Ctx | None], State]:
    """Compile a plan to an executable function."""
    return _compile_plan(implementation, plan, choose_fn=choose_fn, aggregate_fn=aggregate_fn)

