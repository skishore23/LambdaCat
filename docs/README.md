# LambdaCat Documentation

> **Category Theory & Functional Programming Library for Python**

## Overview

LambdaCat is a production-ready functional programming and category theory toolkit that provides:

- **1-Categories** with composition, identities, and law checking
- **Complete FP Stack** (Functor → Applicative → Monad) with verified instances
- **Kleisli Categories** for monadic composition
- **Optics Framework** (Lenses, Prisms, Isomorphisms)
- **Agent Framework** with Plan DSL and Kleisli compilation
- **Diagram Rendering** (Mermaid, DOT) with commutativity checking

## Quick Start

```python
from LambdaCat.core import obj, arrow, build_presentation
from LambdaCat.core.fp.instances.option import Option

# Create a category
A, B = obj("A"), obj("B")
f = arrow("f", "A", "B")
C = build_presentation([A, B], [f])

# Use functional programming
result = Option.some(5).map(lambda x: x * 2).bind(
    lambda x: Option.some(x + 1)
)
print(result)  # Option.some(11)
```

## Installation

```bash
git clone <repository>
cd LambdaCat
pip install -e .
```

## Core Modules

### Categories
- `core.presentation` - Category presentations and formal paths
- `core.category` - Category operations and composition
- `core.builder` - Category construction utilities
- `core.ops` - Basic category operations
- `core.standard` - Standard category constructors

### Functional Programming
- `core.fp.typeclasses` - Functor, Applicative, Monad protocols
- `core.fp.instances` - Concrete implementations (Option, Result, State, Reader, Writer)
- `core.fp.kleisli` - Kleisli arrows and categories

### Advanced Features
- `core.functor` - Functor implementation
- `core.natural` - Natural transformations
- `core.optics` - Lenses, Prisms, Isomorphisms
- `core.diagram` - Diagram construction and rendering

### Agents
- `agents.actions` - Plan DSL (Task, Sequence, Parallel, etc.)
- `agents.runtime` - Plan compilation and execution
- `agents.eval` - Plan evaluation and tracing

### Laws
- `core.laws` - Generic law framework
- `core.laws_category` - Category laws
- `core.laws_functor` - Functor laws
- `core.laws_applicative` - Applicative laws
- `core.laws_monad` - Monad laws

## Examples

See `examples/` folder for working demonstrations:

- `cookbook_10_snippets.py` - Complete feature showcase
- `core_walkthrough.ipynb` - Core concepts tutorial
- `agents_demo.py` - Agent framework usage

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_complete_demo.py -v
```

## API Reference

### Category Construction

```python
from LambdaCat.core import obj, arrow, build_presentation

# Create objects and arrows
A, B = obj("A"), obj("B")
f = arrow("f", "A", "B")

# Build category
C = build_presentation([A, B], [f])
```

### Functional Programming

```python
from LambdaCat.core.fp.instances.option import Option

# Functor
doubled = Option.some(42).map(lambda x: x * 2)

# Applicative
add_func = Option.some(lambda x: x + 10)
result = add_func.ap(Option.some(5))

# Monad
result = Option.some(5).bind(
    lambda x: Option.some(x * 2)
)
```

### Law Checking

```python
from LambdaCat.core.laws import run_suite
from LambdaCat.core.laws_functor import FUNCTOR_SUITE

option = Option.some(42)
report = run_suite(option, FUNCTOR_SUITE, config={"test_value": 42})
print(f"Laws pass: {report.ok}")
```
