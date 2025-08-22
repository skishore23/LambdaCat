<p align="center">
  <img src="./LambdaCat.png" alt="LambdaCat Logo" width="450"/>
</p>

# 🐾 LambdaCat

> Composable agents on a typed categorical core: objects, functors, naturality, and runtime law checks.

## ✨ Features

- 🧮 **Core Category Theory**: Objects, morphisms, composition, identities, functors, natural transformations
- 🔍 **Law Checking**: Executable law suites for categories, functors, applicatives, and monads
- 🧠 **Functional Programming**: Functor, Applicative, Monad typeclasses with concrete instances
- 🤖 **Agent Framework**: Composable plan DSL with `sequence`, `parallel`, `choose`, `focus`, and `loop_while`
- 📊 **Diagram Rendering**: Mermaid and Graphviz DOT formats for categories and plans
- 🎯 **Strong Typing**: Full mypy support with strict typing throughout
- 🚀 **Advanced Features**: Limits/colimits, adjunctions, and Kleisli category builder

---

## 🧠 Philosophy

**LambdaCat** is a functional programming library built on category theory principles. Core principles:

- 🧩 **Functional & Composable**: Small pure functions orchestrated at the edges
- 🏗️ **Category Theory Core**: Minimal, law-centric implementations

---

## 🛠️ Setup

Create a virtual environment and install the package locally:

```bash
python -m venv .venv
source ./.venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

---

## 🚀 Quick Start

### Core Category Theory

```python
from LambdaCat.core import obj, arrow, build_presentation, Cat

# Build a simple category
A = obj("A")
B = obj("B")
f = arrow("f", "A", "B")

presentation = build_presentation([A, B], [f])
C = Cat.from_presentation(presentation)

# Test composition and identities
result = C.compose("f", "id:A")  # Returns "f"
id_A = C.identity("A")           # Returns "id:A"
```

### Standard Categories

```python
from LambdaCat.core.standard import discrete, simplex, walking_isomorphism

# Discrete category (only identities)
D = discrete(["A", "B", "C"])

# Simplex category (0→1→2→...)
Delta2 = simplex(2)
result = Delta2.compose("1->2", "0->1")  # Returns "0->2"

# Walking isomorphism
Iso = walking_isomorphism()
```

### Functional Programming

```python
from LambdaCat.core.fp.instances.option import Option
from LambdaCat.core.fp.instances.result import Result

# Option monad
some_value = Option.some(42)
doubled = some_value.map(lambda x: x * 2)  # Option.some(84)
result = some_value.bind(lambda x: Option.some(x + 1))  # Option.some(43)

# Result monad
success = Result.ok(42)
failure = Result.err("error")
```

### Agent Framework

```python
from LambdaCat.agents.actions import Task, sequence, parallel, choose
from LambdaCat.agents.runtime import compile_plan

# Define actions
actions = {
    "increment": lambda x: x + 1,
    "double": lambda x: x * 2,
    "to_upper": lambda x: x.upper()
}

# Create plans
simple_plan = sequence(Task("increment"), Task("double"))
parallel_plan = parallel(Task("increment"), Task("double"))
choice_plan = choose(Task("to_upper"), Task("double"))

# Compile and execute
executable = compile_plan(actions, simple_plan)
result = executable(5)  # Returns 12

# With aggregation for parallel
executable = compile_plan(actions, parallel_plan, 
                         aggregate_fn=lambda xs: xs[0])
result = executable(5)  # Returns 6 (increment result)
```

---

## 🔬 Core Modules

### `LambdaCat.core`
- **`presentation.py`**: `Obj`, `ArrowGen`, `Formal1`, `Presentation`
- **`category.py`**: `Cat` with identities, composition table, opposite category
- **`builder.py`**: `obj()`, `arrow()`, `build_presentation()`
- **`ops_category.py`**: `identity()`, `compose()`, `normalize()` on `Formal1`
- **`functor.py`**: `Functor` with object/morphism maps
- **`natural.py`**: `Natural` transformations with naturality checks

### `LambdaCat.core.fp`
- **`typeclasses.py`**: Functor, Applicative, Monad protocols
- **`instances/`**: Option, Result, Reader, Writer, State monads
- **`kleisli.py`**: `Kleisli` arrows for monadic composition

### `LambdaCat.core.standard`
- **`discrete()`**: Categories with only identity morphisms
- **`simplex(n)`**: Linear categories 0→1→2→...→n
- **`walking_isomorphism()`**: Two-object category with isomorphism
- **`terminal_category()`**: Single object with single morphism

### `LambdaCat.agents`
- **`actions.py`**: Plan DSL (`Task`, `Sequence`, `Parallel`, `Choose`, `Focus`, `LoopWhile`)
- **`runtime.py`**: `compile_plan()`, `compile_to_kleisli()` for plan execution

---

## 🧪 Testing & Development

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

## 📚 Documentation

- **Complete Manual**: `docs/LambdaCat-CompleteManual.md` - Comprehensive examples and API reference
- **Cookbook**: `examples/cookbook_10_snippets.ipynb` - 10 runnable examples
- **Agent Demo**: `examples/agents_demo.py` - Working agent examples

---

## 🎯 Current Status

✅ **Core Category Theory**: Objects, morphisms, functors, natural transformations  
✅ **Law Checking**: Categories, functors, applicatives, monads  
✅ **FP Typeclasses**: Functor, Applicative, Monad with concrete instances  
✅ **Agent Framework**: Plan DSL with compilation and execution  
✅ **Diagram Rendering**: Mermaid and DOT formats  
✅ **Strong Typing**: Full mypy compliance  
✅ **Advanced Features**: Limits, adjunctions, Kleisli categories

---