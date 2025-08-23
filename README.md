<p align="center">
  <img src="./LambdaCat.png" alt="LambdaCat Logo" width="450"/>
</p>

# 🐾 LambdaCat

A practical functional programming library grounded in category theory.

## Features

**Core Category Theory**: Complete implementation of categories with objects, morphisms, composition, and identities. Includes functors and natural transformations.

**Law Checking**: Built-in test suites that verify mathematical laws for categories, functors, applicatives, and monads at runtime.

**Functional Programming**: Standard typeclasses (Functor, Applicative, Monad) with implementations for Option, Result, Reader, Writer, and State.

**Agent Framework**: Plan execution system with composable operations like `sequence`, `parallel`, `choose`, and `focus`.

**Diagram Rendering**: Export categories and computation plans to Mermaid and Graphviz formats.


**Advanced Features**: Limits, colimits, adjunctions, and Kleisli category construction.

---

## Why LambdaCat?

Category theory provides a rigorous foundation for functional programming. LambdaCat makes these concepts accessible and practical:

- **Composable**: Build complex behavior from simple, well-tested components
- **Verifiable**: Mathematical laws are checked automatically

---

## Setup

```bash
python -m venv .venv
source ./.venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

---

## Quick Start

### Basic Categories

```python
from LambdaCat.core import obj, arrow, build_presentation, Cat

# Create a category with objects and morphisms
A = obj("A")
B = obj("B")
f = arrow("f", "A", "B")

presentation = build_presentation([A, B], [f])
C = Cat.from_presentation(presentation)

# Composition works as expected
result = C.compose("f", "id:A")  # Returns "f"
```

### Standard Categories

```python
from LambdaCat.core.standard import discrete, simplex, walking_isomorphism

# Discrete category - only identity arrows
D = discrete(["A", "B", "C"])

# Simplex category - linear ordering 0→1→2→...
Delta2 = simplex(2)
result = Delta2.compose("1->2", "0->1")  # "0->2"

# Walking isomorphism - two objects with inverse arrows
Iso = walking_isomorphism()
```

### Functional Programming

```python
from LambdaCat.core.fp.instances.option import Option
from LambdaCat.core.fp.instances.result import Result

# Option handles nullable values
value = Option.some(42)
doubled = value.map(lambda x: x * 2)
chained = value.bind(lambda x: Option.some(x + 1))

# Result handles success/failure
success = Result.ok(42)
failure = Result.err("something went wrong")
```

### Agents

```python
from LambdaCat.agents.actions import Task, sequence, parallel, choose
from LambdaCat.agents.runtime import compile_plan

# Define some actions
actions = {
    "increment": lambda x: x + 1,
    "double": lambda x: x * 2,
    "to_upper": lambda x: x.upper()
}

# Build execution plans
simple_plan = sequence(Task("increment"), Task("double"))
parallel_plan = parallel(Task("increment"), Task("double"))
choice_plan = choose(Task("to_upper"), Task("double"))

# Execute plans
executable = compile_plan(actions, simple_plan)
result = executable(5)  # 12

# Parallel execution with aggregation
executable = compile_plan(actions, parallel_plan, 
                         aggregate_fn=lambda results: results[0])
result = executable(5)  # 6

# Choice with selection strategy
executable = compile_plan(actions, choice_plan,
                         choose_fn=lambda options: 0)
result = executable("hello")  # "HELLO"
```

---

## Core Modules

**LambdaCat.core** - Category theory fundamentals
- `presentation.py` - Objects, arrows, and formal presentations  
- `category.py` - Categories with composition and identities
- `builder.py` - Helper functions for building categories
- `ops_category.py` - Category operations and transformations
- `functor.py` - Functors between categories
- `natural.py` - Natural transformations

**LambdaCat.core.fp** - Functional programming
- `typeclasses.py` - Functor, Applicative, Monad protocols
- `instances/` - Concrete implementations (Option, Result, Reader, Writer, State)
- `kleisli.py` - Kleisli arrows for monadic composition

**LambdaCat.core.standard** - Common categories
- `discrete()` - Categories with only identities
- `simplex(n)` - Linear chains 0→1→2→...→n
- `walking_isomorphism()` - Two objects with inverse arrows
- `terminal_category()` - Single object category

**LambdaCat.agents** - Plan execution
- `actions.py` - Plan combinators (Task, Sequence, Parallel, Choose, Focus, LoopWhile)
- `runtime.py` - Plan compilation and execution

---

## Development

Run tests:
```bash
pytest
```

Type checking:
```bash
mypy --strict src/
```

Linting:
```bash
ruff check .
```

---

## Documentation

**Complete Manual**: `docs/LambdaCat-CompleteManual.md` - Full API reference with examples

**Notebooks**: `examples/` directory contains interactive tutorials

**Agent Guide**: `docs/agents_parallel_choose_guide.md` - In-depth guide for parallel and choice operations

---