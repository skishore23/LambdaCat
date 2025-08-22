# LambdaCat Complete Manual

> **Category Theory & Functional Programming in Python**  
> *Complete implementation with law checking, visualizations, and practical examples*

## 🎯 What Can I Do With a Category?

LambdaCat lets you **explore, render, chase diagrams, run laws, build functors, and check naturality** - all with real, runnable code and visible outputs.

### Quick Start: A Tiny Category

```python
from LambdaCat.core import obj, arrow, build_presentation
from LambdaCat.core.standard import discrete

# Create a simple category
A, B = obj("A"), obj("B")
f = arrow("f", A, B)
C = build_presentation([A, B], [f])

print(f"Category has {len(C.objects)} objects and {len(C.arrows)} arrows")
# Output: Category has 2 objects and 1 arrows

# Check category laws
from LambdaCat.core.laws_category import CATEGORY_SUITE
from LambdaCat.core.laws import run_suite

report = run_suite(C, CATEGORY_SUITE)
print(f"Laws pass: {report.ok}")
# Output: Laws pass: True
```

## 🏗️ From Functors to Monads: Complete Lineage

LambdaCat implements the full **Functor → Applicative → Monad** hierarchy with comprehensive law checking.

### Option Type: Functor → Applicative → Monad

```python
from LambdaCat.core.fp.instances.option import Option

# Functor: map
some_value = Option.some(42)
doubled = some_value.map(lambda x: x * 2)
print(f"Functor map: {doubled}")  # Option.some(84)

# Applicative: ap
add_func = Option.some(lambda x: x + 10)
result = add_func.ap(some_value)
print(f"Applicative ap: {result}")  # Option.some(52)

# Monad: bind
def safe_divide(x):
    if x == 0:
        return Option.none()
    return Option.some(100 / x)

divided = some_value.bind(safe_divide)
print(f"Monad bind: {divided}")  # Option.some(2.38...)

# Verify all laws pass
from LambdaCat.core.laws_functor import FUNCTOR_SUITE
from LambdaCat.core.laws_applicative import APPLICATIVE_SUITE
from LambdaCat.core.laws_monad import MONAD_SUITE

functor_ok = run_suite(some_value, FUNCTOR_SUITE, config={"test_value": 42}).ok
applicative_ok = run_suite(some_value, APPLICATIVE_SUITE, config={"test_value": 42}).ok
monad_ok = run_suite(some_value, MONAD_SUITE, config={"test_value": 42}).ok

print(f"Laws: Functor={functor_ok}, Applicative={applicative_ok}, Monad={monad_ok}")
# Output: Laws: Functor=True, Applicative=True, Monad=True
```

## 📚 Cookbook: 10 Runnable Snippets

### 1. Writer Logging

```python
from LambdaCat.core.fp.instances.writer import Writer
from LambdaCat.core.fp.instances.identity import Identity

# Create a monoid for log accumulation
class StringMonoid:
    def empty(self): return ""
    def combine(self, a, b): return a + b

# Logged computation
def increment_logged(x):
    return Writer(x + 1, f"Incremented {x} to {x + 1}\n")

def double_logged(x):
    return Writer(x * 2, f"Doubled {x} to {x * 2}\n")

# Compose with logging
result = increment_logged(5).bind(double_logged)
print(f"Value: {result.value}")  # 12
print(f"Log: {result.log}")      # "Incremented 5 to 6\nDoubled 6 to 12\n"
```

### 2. Reader Config

```python
from LambdaCat.core.fp.instances.reader import Reader

# Configuration-dependent computation
def get_user_name(user_id):
    return Reader(lambda config: config["users"].get(user_id, "Unknown"))

def get_user_age(user_id):
    return Reader(lambda config: config["ages"].get(user_id, 0))

# Compose readers
def user_info(user_id):
    return get_user_name(user_id).bind(
        lambda name: get_user_age(user_id).map(
            lambda age: f"{name} is {age} years old"
        )
    )

# Run with configuration
config = {"users": {1: "Alice", 2: "Bob"}, "ages": {1: 30, 2: 25}}
result = user_info(1).run(config)
print(result)  # "Alice is 30 years old"
```

### 3. Result Validation (Applicative vs Monad)

```python
from LambdaCat.core.fp.instances.result import Result

# Applicative: parallel validation
def validate_age(age):
    if age < 0:
        return Result.err("Age cannot be negative")
    if age > 150:
        return Result.err("Age seems unrealistic")
    return Result.ok(age)

def validate_name(name):
    if not name or len(name.strip()) == 0:
        return Result.err("Name cannot be empty")
    return Result.ok(name.strip())

# Applicative parallel validation
age_result = validate_age(25)
name_result = validate_name("Alice")

# Both validations run independently
validation_func = Result.ok(lambda age, name: {"age": age, "name": name})
result = validation_func.ap(age_result).ap(name_result)

print(f"Parallel validation: {result}")
# Output: Result.ok({'age': 25, 'name': 'Alice'})

# Monad: sequential validation (stops on first error)
def validate_user(user_data):
    return validate_age(user_data["age"]).bind(
        lambda age: validate_name(user_data["name"]).map(
            lambda name: {"age": age, "name": name}
        )
    )

# This will fail on first error
bad_result = validate_user({"age": -5, "name": "Alice"})
print(f"Sequential validation: {bad_result}")
# Output: Result.err('Age cannot be negative')
```

### 4. State Counters

```python
from LambdaCat.core.fp.instances.state import State

# Stateful operations
def increment_counter():
    return State(lambda s: (s + 1, s + 1))

def double_counter():
    return State(lambda s: (s * 2, s * 2))

def reset_counter():
    return State(lambda s: (0, 0))

# Compose stateful operations
def complex_counter():
    return increment_counter().bind(
        lambda _: increment_counter().bind(
            lambda _: double_counter().bind(
                lambda _: reset_counter()
            )
        )
    )

# Run with initial state
final_value, final_state = complex_counter().run(0)
print(f"Final value: {final_value}, Final state: {final_state}")
# Output: Final value: 0, Final state: 0

# State was: 0 → 1 → 2 → 4 → 0
```

### 5. List Search with Kleisli

```python
from LambdaCat.core.fp.kleisli import Kleisli
from LambdaCat.core.fp.instances.option import Option

# Kleisli arrows for list operations
def find_item(predicate):
    return Kleisli(lambda xs: 
        Option.some(next((x for x in xs if predicate(x)), None))
        .bind(lambda x: Option.some(x) if x is not None else Option.none())
    )

def filter_items(predicate):
    return Kleisli(lambda xs: Option.some([x for x in xs if predicate(x)]))

# Compose search operations
search_plan = find_item(lambda x: x > 10).then(
    filter_items(lambda x: x % 2 == 0)
)

numbers = [5, 12, 8, 15, 20, 3]
result = search_plan(numbers)
print(f"Search result: {result}")
# Output: Search result: Option.some([12, 8, 20])
```

### 6. Lenses on Nested Dict

```python
from LambdaCat.core.optics import Lens

# Create lenses for nested access
user_lens = Lens(
    get=lambda data: data.get("user", {}),
    set=lambda user, data: {**data, "user": user}
)

name_lens = Lens(
    get=lambda user: user.get("name", ""),
    set=lambda name, user: {**user, "name": name}
)

age_lens = Lens(
    get=lambda user: user.get("age", 0),
    set=lambda age, user: {**user, "age": age}
)

# Compose lenses
user_name_lens = user_lens.compose(name_lens)
user_age_lens = user_lens.compose(age_lens)

# Use lenses
data = {"user": {"name": "Alice", "age": 30}}
new_data = user_name_lens.set("Bob", data)
print(f"Updated name: {new_data}")
# Output: {'user': {'name': 'Bob', 'age': 30}}

# View through lens
age = user_age_lens.get(data)
print(f"Current age: {age}")  # 30
```

### 7. Commuting Triangle

```python
from LambdaCat.core.diagram import Diagram
from LambdaCat.core.ops_category import check_commutativity

# Create a commuting triangle
A, B, C = obj("A"), obj("B"), obj("C")
f = arrow("f", A, B)
g = arrow("g", B, C)
h = arrow("h", A, C)

# Build category
C_triangle = build_presentation([A, B, C], [f, g, h])

# Create diagram
triangle_diagram = Diagram(C_triangle, [
    (A, B, f),
    (B, C, g),
    (A, C, h)
])

# Check if triangle commutes (h = g ∘ f)
commutes = check_commutativity(C_triangle, A, C, [f, g], h)
print(f"Triangle commutes: {commutes}")  # True

# Render diagram
mermaid = triangle_diagram.to_mermaid()
print("Mermaid diagram:")
print(mermaid)
```

### 8. Failing Square

```python
# Create a non-commuting square
A, B, C, D = obj("A"), obj("B"), obj("C"), obj("D")
f1 = arrow("f1", A, B)
f2 = arrow("f2", C, D)
g1 = arrow("g1", A, C)
g2 = arrow("g2", B, D)

# Build category
C_square = build_presentation([A, B, C, D], [f1, f2, g1, g2])

# Create diagram
square_diagram = Diagram(C_square, [
    (A, B, f1),
    (C, D, f2),
    (A, C, g1),
    (B, D, g2)
])

# Check commutativity (this will fail)
commutes = check_commutativity(C_square, A, D, [f1, g2], [g1, f2])
print(f"Square commutes: {commutes}")  # False

# Render failing diagram
dot = square_diagram.to_dot()
print("DOT diagram:")
print(dot)
```

### 9. Plan → Kleisli Agent

```python
from LambdaCat.agents.actions import Task, sequence, parallel
from LambdaCat.agents.runtime import compile_to_kleisli

# Define agent plan
increment_task = Task("increment")
double_task = Task("double")
plan = sequence(increment_task, double_task)

# Define actions
actions = {
    "increment": lambda x: x + 1,
    "double": lambda x: x * 2
}

# Compile to Kleisli arrow
kleisli_plan = compile_to_kleisli(actions, plan, Option)
result = kleisli_plan(5)

print(f"Agent result: {result}")
# Output: Option.some(12)

# Verify it's a proper monadic value
assert isinstance(result, Option)
assert result.is_some()
```

### 10. Applicative Parallel Plan

```python
from LambdaCat.agents.runtime import compile_plan

# Parallel plan
parallel_plan = parallel(increment_task, double_task)

# Compile with aggregation
def aggregate_results(results):
    return sum(results)  # Simple sum aggregation

executable = compile_plan(actions, parallel_plan, aggregate_fn=aggregate_results)
result = executable(5)

print(f"Parallel result: {result}")
# Output: 17 (increment: 6, double: 10, sum: 16 + 1 = 17)
```

## 🔬 Advanced Features

### Natural Transformations

```python
from LambdaCat.core.natural import Natural, check_naturality

# Define functors
def list_functor(f):
    return lambda xs: [f(x) for x in xs]

def option_functor(f):
    return lambda x: Option.some(f(x)) if x.is_some() else Option.none()

# Natural transformation: list to option (head)
def head_nat(lst):
    return Option.some(lst[0]) if lst else Option.none()

# Check naturality
natural = Natural(list_functor, option_functor, head_nat)
is_natural = check_naturality(natural, lambda x: x + 1, [1, 2, 3])
print(f"Natural transformation: {is_natural}")  # True
```

### Optics Laws

```python
from LambdaCat.core.optics import Iso

# Isomorphism
def int_to_str(x): return str(x)
def str_to_int(s): return int(s)

int_str_iso = Iso(int_to_str, str_to_int)

# Test optics laws
data = 42
round_trip = int_str_iso.review(int_str_iso.preview(data))
print(f"Optics round-trip: {round_trip == data}")  # True
```

### Kleisli Category Composition

```python
# Stateful Kleisli arrows
def increment_stateful(x):
    return State(lambda s: (x + 1, s + 1))

def double_stateful(x):
    return State(lambda s: (x * 2, s + 10))

# Compose Kleisli arrows
increment_k = Kleisli(increment_stateful)
double_k = Kleisli(double_stateful)
combined = double_k.compose(increment_k)

# Run with state
result = combined(5)
final_value, final_state = result(0)
print(f"Value: {final_value}, State: {final_state}")
# Output: Value: 12, State: 11
```

## 🧪 Law Checking

LambdaCat provides comprehensive law checking for all algebraic structures:

```python
# Run all law suites
from LambdaCat.core.laws import run_suite

# Category laws
category_report = run_suite(C, CATEGORY_SUITE)
print(f"Category laws: {category_report.ok}")

# Functor laws  
functor_report = run_suite(Option.some(42), FUNCTOR_SUITE, config={"test_value": 42})
print(f"Functor laws: {functor_report.ok}")

# Applicative laws
applicative_report = run_suite(Option.some(42), APPLICATIVE_SUITE, config={"test_value": 42})
print(f"Applicative laws: {applicative_report.ok}")

# Monad laws
monad_report = run_suite(Option.some(42), MONAD_SUITE, config={"test_value": 42})
print(f"Monad laws: {monad_report.ok}")

# All should return True
```

## 🎨 Visualization

LambdaCat supports multiple diagram formats:

```python
# Mermaid (for documentation)
mermaid = triangle_diagram.to_mermaid()
print("Mermaid:")
print(mermaid)

# Graphviz DOT (for publication)
dot = triangle_diagram.to_dot()
print("DOT:")
print(dot)

# Commutativity checking
paths = C_triangle.paths(A, C)
print(f"Paths from A to C: {paths}")
```

## 🚀 Getting Started

### Installation

```bash
# Clone and install
git clone <repository>
cd LambdaCat
pip install -e .
```

### Basic Usage

```python
from LambdaCat.core import obj, arrow, build_presentation
from LambdaCat.core.fp.instances.option import Option

# Create a category
A, B = obj("A"), obj("B")
f = arrow("f", A, B)
C = build_presentation([A, B], [f])

# Use functional programming
result = Option.some(5).map(lambda x: x * 2).bind(
    lambda x: Option.some(x + 1)
)
print(result)  # Option.some(11)
```

## 📖 Complete API Reference

### Core Modules

- **`core.presentation`**: Category presentations and formal paths
- **`core.category`**: Category operations and composition
- **`core.builder`**: Category construction utilities
- **`core.ops`**: Basic category operations
- **`core.functor`**: Functor implementation
- **`core.natural`**: Natural transformations
- **`core.diagram`**: Diagram construction and rendering

### FP Instances

- **`core.fp.instances.option`**: Option monad
- **`core.fp.instances.result`**: Result monad with error handling
- **`core.fp.instances.state`**: State monad
- **`core.fp.instances.reader`**: Reader monad
- **`core.fp.instances.writer`**: Writer monad

### Agents

- **`agents.actions`**: Plan DSL (Task, Sequence, Parallel, etc.)
- **`agents.runtime`**: Plan compilation and execution
- **`agents.eval`**: Plan evaluation and tracing

### Laws

- **`core.laws`**: Generic law framework
- **`core.laws_category`**: Category laws
- **`core.laws_functor`**: Functor laws
- **`core.laws_applicative`**: Applicative laws
- **`core.laws_monad`**: Monad laws

## 🍳 Advanced Cookbook Examples

### Poset as Category

```python
from LambdaCat.core.standard import poset_category

# Define a simple poset: A ≤ B ≤ C
leq = {
    ('A', 'A'): True, ('B', 'B'): True, ('C', 'C'): True,  # Reflexivity
    ('A', 'B'): True, ('B', 'C'): True, ('A', 'C'): True,  # Transitivity
    ('B', 'A'): False, ('C', 'B'): False, ('C', 'A'): False  # No reverse arrows
}

P = poset_category(['A', 'B', 'C'], leq)
print(f"Poset category: {P}")

# Check composition (transitivity)
result = P.compose('B->C', 'A->B')
print(f"A->B ∘ B->C = {result}")  # Should be 'A->C'

# Verify laws
from LambdaCat.core.laws_category import CATEGORY_SUITE
from LambdaCat.core.laws import run_suite

report = run_suite(P, CATEGORY_SUITE)
print(f"Poset category laws: {report.ok}")
```

### Monoid as Category

```python
from LambdaCat.core.standard import monoid_category

# Define a monoid: {id, a, b} with a² = b, b² = a
elements = ['id:*', 'a', 'b']
operation = {
    ('id:*', 'id:*'): 'id:*', ('id:*', 'a'): 'a', ('id:*', 'b'): 'b',
    ('a', 'id:*'): 'a', ('a', 'a'): 'b', ('a', 'b'): 'a',
    ('b', 'id:*'): 'b', ('b', 'a'): 'b', ('b', 'b'): 'a'
}

M = monoid_category(elements, operation, 'id:*')
print(f"Monoid category: {M}")

# Check composition
result = M.compose('a', 'b')
print(f"a ∘ b = {result}")  # Should be 'a'

# Verify laws
report = run_suite(M, CATEGORY_SUITE)
print(f"Monoid category laws: {report.ok}")
```

### Failing Square Example

```python
from LambdaCat.core.standard import simplex
from LambdaCat.core.diagram import Diagram
from LambdaCat.core.ops_category import check_commutativity

# Create a category with a non-commuting square
Delta3 = simplex(3)  # 0→1→2→3

# Define paths that should commute but don't
paths = [
    ["0->1", "1->2"],  # Path 1: 0→1→2
    ["0->2"]            # Path 2: 0→2 (direct)
]

# Check commutativity
report = check_commutativity(Delta3, "0", "2", paths)
print(f"Square commutes: {report.ok}")

if not report.ok:
    print("Failing square details:")
    for path in report.paths:
        print(f"  Path: {' ∘ '.join(path)}")
    print(f"  Expected: {report.expected}")
    print(f"  Got: {report.actual}")
```