# Agents

Minimal, composable pipelines built from named actions.

## API surface (canonical)

```python
from LambdaCat.agents import (
  task, sequence, parallel, choose, lens, focus, loop_while,
  strong_monoidal_functor, compile_structured_plan,
  Agent, run_plan, run_structured_plan, choose_best, quick_functor_laws,
)
```

Notes:
- Linear pipelines: construct `Formal1(('a','b',...))` from `LambdaCat.core.presentation`.
- `sequence`/`parallel` express tree-shaped plans; `parallel` requires an explicit aggregator at run-time.
- `choose` requires an explicit chooser at run-time.

## Terminology

- **Action**: a pure function `(x) -> y` or `(x, ctx) -> y` that transforms data. You implement actions.
- **Task**: a plan leaf that calls a named action. You compose tasks into plans.
- **Plan**: a composition of tasks. Two styles:
  - Sequential plan as a formal word `Formal1(('a','b',...))`
  - Structured plan using builders: `task`, `sequence`, `parallel`, `choose`, plus `focus` and `loop_while`
- **Sequence**: run child plans left-to-right.
- **Parallel**: run child plans concurrently and combine outputs via an explicit `aggregate_fn`.
- **Choose**: evaluate child plans and pick one via an explicit `choose_fn`.
- **Agent**: convenience wrapper for running plans and selecting the best among candidates with an evaluator.

## Typing

- `Action[State, Ctx]`: callables `(State) -> State` or `(State, Ctx) -> State`.
- `Plan[State, Ctx]`: typed plan tree composed from `Task`, `Sequence`, `Parallel`, `Choose`, `Focus`, `LoopWhile`.
- Runners:
  - `strong_monoidal_functor(impl)` compiles `Formal1` to `(State, Ctx?) -> State`.
  - `compile_structured_plan(impl, plan, ..., choose_fn?, aggregate_fn?)` returns `(State, Ctx?) -> State`.

If the names feel similar, remember: Task calls an Action. Actions are functions; Tasks are nodes in a plan.

## Plan tree

- The plan is an immutable, typed tree of nodes: `Task`, `Sequence`, `Parallel`, `Choose`.
- It is an abstract syntax tree for the LambdaCat agent DSL, not Python’s AST.
- Its semantics are defined by the interpreter:
  - `Sequence`: ordered composition (feed-forward through children)
  - `Parallel`: fan-out to children, then aggregate outputs with `aggregate_fn`
  - `Choose`: evaluate branches, then select exactly one via `choose_fn`
- This tree is a pure data structure (no side effects), suitable for tracing, testing, or serialization.

## Define actions
```python
actions = {
  'denoise': lambda s, ctx=None: s.replace('~',''),
  'edges':   lambda s, ctx=None: ''.join(ch for ch in s if ch.isalpha()),
  'segment': lambda s, ctx=None: s.upper(),
  'merge':   lambda s, ctx=None: f"[{s}]",
}
```

## Compose a plan
```python
from LambdaCat.core.presentation import Formal1
plan = Formal1(('denoise','edges','segment','merge'))
```

## Run and score
```python
from LambdaCat.agents import Agent
agent = Agent(actions, evaluator=lambda o: -len(o), snapshot=True)
report = agent.run(plan, "~a~b_c-1")
print(report.output, report.score)
```

## Choose best among candidates
```python
from LambdaCat.agents import choose_best
best_plan, best_report = choose_best(
  [plan, Formal1(('denoise','segment','merge'))],
  actions,
  "~a~b_c-1",
  evaluator=lambda o: -len(o),
)
```

## Structured plans (Sequence / Parallel / Choose)

```python
from LambdaCat.agents.actions import task, sequence, parallel, choose, lens, focus, loop_while
from LambdaCat.agents.eval import run_structured_plan

structured = sequence(
  task('denoise'),
  parallel(task('edges'), task('segment')),
  task('merge'),
)

report = run_structured_plan(
  structured,
  actions,
  input_value="~a~b_c-1",
  aggregate_fn=lambda outs: ''.join(outs),   # combine Parallel outputs
  choose_fn=None,                            # not used here
  snapshot=True,
)
print(report.output)
```

```python
# Choose example: pick best branch by a custom chooser
branching = choose(task('segment'), task('merge'))
best = run_structured_plan(
  branching,
  actions,
  input_value="ab",
  choose_fn=lambda outs: max(range(len(outs)), key=lambda i: len(str(outs[i]))),
  aggregate_fn=None,
)
print(best.output)
```

## Focused transforms (Lens)

```python
from dataclasses import replace
from LambdaCat.agents.actions import task, sequence, lens, focus

# state is a dict; focus on key 'text'
get_text = lambda s: s['text']
set_text = lambda s, v: {**s, 'text': v}
txt = lens(get_text, set_text)

inner = sequence(task('denoise'), task('segment'))
plan = focus(txt, inner)
```

## Loops

```python
from LambdaCat.agents.actions import loop_while, task, sequence

predicate = lambda s: '~~' in s
body = task('denoise')
plan = loop_while(predicate, sequence(body))
```

## Functor sanity checks (empirical)
```python
from LambdaCat.agents import quick_functor_laws
quick_functor_laws({'f': lambda x: x+1, 'g': lambda x: x*2, 'id': lambda x: x}, id_name='id', samples=[0,1,2])
```

## Design constraints
- Actions must accept `(x)` or `(x, ctx)`
- Unsupported modes raise
- Deterministic execution; traces carry per-step timings and snapshots
