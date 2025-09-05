from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ..actions import Choose, Focus, LoopWhile, Parallel, Plan, Sequence, Task
from .effect import Effect, Err, Ok, with_trace
from .patch import patch_combine

S = TypeVar("S")  # State
Ctx = TypeVar("Ctx")  # Context

# Action registry type - following existing patterns
ActionRegistry = dict[str, Callable[[S, dict[str, object]], S | Effect[S, S]]]


@dataclass(frozen=True)
class ParallelSpec:
    """Specification for parallel execution policies."""
    policy: str = "ALL"  # "ALL" | "FIRST_COMPLETED" | "N_BEST"
    n_best: int = 1  # for N_BEST policy
    timeout_s: float | None = None  # global timeout
    merge_strategy: str = "left_biased"  # state merge strategy


class AsyncCompiler(Generic[S, Ctx]):
    """Compiles Plan AST to Effect monads with true parallelism.

    This is the natural transformation from the Plan DSL to the Effect monad,
    preserving the categorical structure while enabling async execution.
    """

    def __init__(
        self,
        actions: ActionRegistry[S],
        merge_state: Callable[[S, S], S] | None = None,
        enable_tracing: bool = True,
        default_parallel_spec: ParallelSpec | None = None
    ):
        self.actions = actions
        self.merge_state = merge_state or patch_combine
        self.enable_tracing = enable_tracing
        self.default_parallel_spec = default_parallel_spec or ParallelSpec()

    def compile(self, plan: Plan[S, Ctx]) -> Effect[S, S]:
        """Compile a plan to an Effect.

        This is the main entry point for the natural transformation:
        Plan -> Effect[S, S]
        """
        return self._compile_recursive(plan)

    def _compile_recursive(self, plan: Plan[S, Ctx]) -> Effect[S, S]:
        """Recursively compile plan nodes to Effects.

        This preserves the categorical structure:
        - Task -> Effect (atomic computation)
        - Sequence -> bind composition (monadic)
        - Parallel -> par_mapN (applicative)
        - Choose -> race_first (alternative)
        - Focus -> lens composition (functorial)
        - LoopWhile -> iterative bind (monadic)
        """

        if isinstance(plan, Task):
            return self._compile_task(plan)
        elif isinstance(plan, Sequence):
            return self._compile_sequence(plan)
        elif isinstance(plan, Parallel):
            return self._compile_parallel(plan)
        elif isinstance(plan, Choose):
            return self._compile_choose(plan)
        elif isinstance(plan, Focus):
            return self._compile_focus(plan)
        elif isinstance(plan, LoopWhile):
            return self._compile_loop(plan)
        else:
            raise TypeError(f"Unknown plan type: {type(plan)}")

    def _compile_task(self, task: Task[S, Ctx]) -> Effect[S, S]:
        """Compile a Task to an Effect.

        Tasks are the atomic computations in the plan DSL.
        They can be either sync or async functions.
        """
        if task.name not in self.actions:
            raise KeyError(f"Unknown action: {task.name}")

        action = self.actions[task.name]

        # Check if action returns Effect or plain state
        if asyncio.iscoroutinefunction(action):
            # Async action - lift to Effect
            async def run_async(s: S, ctx: dict[str, object]) -> tuple[S, list[dict[str, object]], Ok[S] | Err[Exception]]:
                try:
                    result = await action(s, ctx)
                    if isinstance(result, Effect):
                        return await result.run(s, ctx)
                    else:
                        return (result, [{"span": f"task:{task.name}"}], Ok(result))
                except Exception as e:
                    return (s, [{"span": f"task:{task.name}", "error": str(e)}], Err(e))

            effect = Effect(run_async)
        else:
            # Sync action - lift to Effect
            async def run_sync(s: S, ctx: dict[str, object]) -> tuple[S, list[dict[str, object]], Ok[S] | Err[Exception]]:
                try:
                    # Handle both single-parameter and two-parameter functions
                    import inspect
                    sig = inspect.signature(action)
                    params = list(sig.parameters.values())

                    if len(params) == 1:
                        result = action(s)
                    elif len(params) == 2:
                        result = action(s, ctx)
                    else:
                        raise TypeError(f"Action must accept 1 (s) or 2 (s, ctx) parameters, got {len(params)}")

                    return (result, [{"span": f"task:{task.name}"}], Ok(result))
                except Exception as e:
                    return (s, [{"span": f"task:{task.name}", "error": str(e)}], Err(e))

            effect = Effect(run_sync)

        # Add tracing if enabled
        if self.enable_tracing:
            return with_trace(f"task:{task.name}", effect)
        else:
            return effect

    def _compile_sequence(self, seq: Sequence[S, Ctx]) -> Effect[S, S]:
        """Compile a Sequence to sequential Effect composition.

        This uses Kleisli composition for proper monadic sequencing.
        """
        if not seq.items:
            return Effect.pure(lambda s: s)  # Identity

        # Compile all items to Effects
        effects = [self._compile_recursive(item) for item in seq.items]

        # Compose sequentially using bind - simpler and more reliable
        result = effects[0]
        for _i, effect in enumerate(effects[1:], 1):
            result = result.bind(lambda _, eff=effect: eff)

        return result

    def _compile_parallel(self, par: Parallel[S, Ctx]) -> Effect[S, S]:
        """Compile a Parallel to parallel Effect composition.

        This uses different policies for parallel execution:
        - ALL: Wait for all branches to complete
        - FIRST_COMPLETED: Return first successful result
        - N_BEST: Return best N results based on evaluator
        """
        if not par.items:
            return Effect.pure(lambda s: s)  # Identity

        # Compile all items
        effects = [self._compile_recursive(item) for item in par.items]

        # Use parallel composition with policy
        return self._compile_parallel_with_policy(effects, self.default_parallel_spec)

    def _compile_parallel_with_policy(self, effects: list[Effect[S, S]], spec: ParallelSpec) -> Effect[S, S]:
        """Compile parallel effects with specific policy."""
        # Apply timeout if specified
        if spec.timeout_s is not None:
            effects = [Effect.timeout(spec.timeout_s, effect) for effect in effects]

        if spec.policy == "ALL":
            return self._compile_parallel_all(effects, spec)
        elif spec.policy == "FIRST_COMPLETED":
            return self._compile_parallel_first(effects, spec)
        elif spec.policy == "N_BEST":
            return self._compile_parallel_n_best(effects, spec)
        else:
            raise ValueError(f"Unknown parallel policy: {spec.policy}")

    def _compile_parallel_all(self, effects: list[Effect[S, S]], spec: ParallelSpec) -> Effect[S, S]:
        """Compile parallel effects with ALL policy."""
        parallel_effect = Effect.par_mapN(self.merge_state, *effects)
        return parallel_effect.map(lambda results: results[-1] if results else None)

    def _compile_parallel_first(self, effects: list[Effect[S, S]], spec: ParallelSpec) -> Effect[S, S]:
        """Compile parallel effects with FIRST_COMPLETED policy."""
        return Effect.race_first(*effects)

    def _compile_parallel_n_best(self, effects: list[Effect[S, S]], spec: ParallelSpec) -> Effect[S, S]:
        """Compile parallel effects with N_BEST policy."""
        # For now, fall back to race_first - evaluator would be needed for proper N_BEST
        return Effect.race_first(*effects)

    def _compile_choose(self, choose: Choose[S, Ctx]) -> Effect[S, S]:
        """Compile a Choose to racing Effect composition.

        This uses Alternative/Alt race_first for choice.
        """
        if not choose.items:
            raise ValueError("Choose with no items")

        # Compile all items
        effects = [self._compile_recursive(item) for item in choose.items]

        # Race them and take the first successful result
        return Effect.race_first(*effects)

    def _compile_focus(self, focus: Focus[S, Ctx, object]) -> Effect[S, S]:
        """Compile a Focus to lens-based Effect composition.

        This uses lens functoriality for state focus.
        """
        inner_effect = self._compile_recursive(focus.inner)

        async def run_with_lens(s: S, ctx: dict[str, object]) -> tuple[S, list[dict[str, object]], Ok[S] | Err[Exception]]:
            # Extract sub-state using lens
            sub_state = focus.lens.get(s)

            # Run inner effect on sub-state
            sub_result, trace, result = await inner_effect.run(sub_state, ctx)

            if isinstance(result, Err):
                return (s, trace, result)

            # Update main state with new sub-state
            new_state = focus.lens.set(s, sub_result)
            return (new_state, trace, Ok(new_state))

        return Effect(run_with_lens)

    def _compile_loop(self, loop: LoopWhile[S, Ctx]) -> Effect[S, S]:
        """Compile a LoopWhile to iterative Effect composition.

        This uses monadic bind in a loop for iteration.
        """
        body_effect = self._compile_recursive(loop.body)

        async def run_loop(s: S, ctx: dict[str, object]) -> tuple[S, list[dict[str, object]], Ok[S] | Err[Exception]]:
            current_state = s
            all_traces = []

            while loop.predicate(current_state):
                # Run body effect
                new_state, trace, result = await body_effect.run(current_state, ctx)
                all_traces.extend(trace)

                if isinstance(result, Err):
                    return (current_state, all_traces, result)

                current_state = new_state

            return (current_state, all_traces, Ok(current_state))

        return Effect(run_loop)


# High-level API functions - following existing patterns
def compile_plan_async(
    plan: Plan[S, Ctx],
    actions: ActionRegistry[S],
    merge_state: Callable[[S, S], S] | None = None,
    enable_tracing: bool = True
) -> Effect[S, S]:
    """Compile a plan to an async Effect with true parallelism.

    This is the main API for the natural transformation from Plan to Effect.
    """
    compiler = AsyncCompiler(actions, merge_state, enable_tracing)
    return compiler.compile(plan)


# High-level API for async plan execution
async def run_plan(
    plan: Plan[S, Ctx],
    actions: ActionRegistry[S],
    initial_state: S,
    context: dict[str, object] | None = None,
    merge_state: Callable[[S, S], S] | None = None,
    enable_tracing: bool = True
) -> tuple[S, list[dict[str, object]], Ok[S] | Err[Exception]]:
    """Run a plan asynchronously - the main execution API."""
    effect = compile_plan_async(plan, actions, merge_state, enable_tracing)
    return await effect.run(initial_state, context or {})
