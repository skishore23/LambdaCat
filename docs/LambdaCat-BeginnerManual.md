# LambdaCat Beginner’s Manual

Welcome to **LambdaCat**, a Python toolkit for categories, functors, and functional programming patterns.  
This manual is for **Python developers, AI researchers, data/game modelers, and agent designers** who want to learn and use category theory ideas in practice.

No prior category theory required — we start from **functions and data** and build up step by step.

---

## 0. What is LambdaCat?

LambdaCat helps you:

- Organize programs as **categories** (objects + arrows).
- Build and verify **functors** (structure-preserving maps).
- Work with **monads** for state, errors, logging, nondeterminism.
- Compose **agents** from plans as categorical functors.
- Draw **diagrams** and check if they commute (agree).

---

## 1. Functions as Arrows

In Python, a function is just an arrow:

```python
def f(x: int) -> str:
    return str(x)

def g(s: str) -> float:
    return float(len(s))

h = lambda x: g(f(x))
print(h(42))  # 2.0
```

This is **composition**: `h = g ∘ f`.

---

## 2. Building Your First Category

A category has:
- Objects (types, states).
- Morphisms (arrows/functions).
- Composition rules.
- Identity arrows.

```python
from lambdacat.core.category import Cat

objects = ["int","str","float"]
morphisms = {
    ("int","int"): ["id_int"],
    ("str","str"): ["id_str"],
    ("float","float"): ["id_float"],
    ("int","str"): ["f"],
    ("str","float"): ["g"],
    ("int","float"): ["gf"],
}
composition = {("f","g"): "gf"}
identities = {"int":"id_int","str":"id_str","float":"id_float"}

C = Cat(objects, morphisms, composition, identities)

print("Objects:", C.objects)
print("Morphisms from int to str:", C.morphisms[("int","str")])
```

Output:
```
Objects: ['int','str','float']
Morphisms from int to str: ['f']
```

---

## 3. Why Laws Matter

Categories must satisfy **laws**:
- Associativity
- Identities

### Example: Good category

```python
from lambdacat.lawsuite import CATEGORY_SUITE
CATEGORY_SUITE.run_suite(C)
```

Output:
```
[✓] Identity laws hold
[✓] Associativity holds
```

### Example: Broken category

```python
C_bad = Cat(["A"], {("A","A"): []}, {}, {})
CATEGORY_SUITE.run_suite(C_bad)
```

Output:
```
[✗] Identity law failed: object 'A' has no identity
```

---

## 4. Drawing and Chasing Diagrams

A diagram is just a picture of arrows.

```python
from lambdacat.render import mermaid

diagram = {
    "objects": ["A","B","C"],
    "morphisms": [
        ("A","B","f"),
        ("B","C","g"),
        ("A","C","h"),
    ]
}
print(mermaid(diagram))
```

You get a graph showing `A --f--> B --g--> C` and `A --h--> C`.

Check if it **commutes**:

```python
from lambdacat.lawsuite import check_commutativity
paths = [["f","g"], ["h"]]
print(check_commutativity(C, "A","C", paths))
```

Output:
```
[✓] Paths f∘g and h agree from A→C
```

---

## 5. Functors: Mapping Categories

A functor maps objects and arrows between categories.

```python
from lambdacat.core.functor import FunctorBuilder

F = FunctorBuilder(C, C)
F.add_object_mapping("int","int")
F.add_morphism_mapping("f","f")
functor = F.build()

from lambdacat.lawsuite import FUNCTOR_SUITE
FUNCTOR_SUITE.run_suite(F)
```

Output:
```
[✓] Preserves identities
[✓] Preserves composition
```

---

## 6. Natural Transformations

A natural transformation aligns two functors `F, G: C → D`.

```python
from lambdacat.core.natural import check_naturality
# Suppose eta maps F(X) → G(X) with component morphisms
check_naturality(F,G,eta)
```

If all squares commute, it’s natural.

---

## 7. From Functors to Monads

### Functors
```python
from lambdacat.data import Option
print(Option.some(3).map(lambda x: x+1))  # Some(4)
```

### Applicatives
```python
add = Option.pure(lambda x,y: x+y)
print(add.ap(Option.some(2)).ap(Option.some(3)))  # Some(5)
```

### Monads
```python
from lambdacat.data import Result

safe_div = lambda x,y: Result.err("div by zero") if y==0 else Result.ok(x/y)
print(Result.ok((10,2)).bind(lambda xy: safe_div(*xy)))  # Ok(5.0)
print(Result.ok((10,0)).bind(lambda xy: safe_div(*xy)))  # Err("div by zero")
```

---

## 8. State and Kleisli Categories

Monads let us model **stateful computations**.

```python
from lambdacat.monads.instances import State, Kleisli

def get(): return State(lambda s: (s,s))
def put(ns): return State(lambda _: (None, ns))

inc = Kleisli(lambda _: get().bind(lambda n: put(n+1)), State)
prog = inc.then(inc).then(inc)

_, s_final = prog.run(None).run(0)
print(s_final)  # 3
```

---

## 9. Optics: Lenses

Work with nested immutable data.

```python
from lambdacat.optics import lens

user = {"name":"Ada","address":{"city":"London"}}
city_lens = lens["address"]["city"]

print(city_lens.get(user))          # London
print(city_lens.set(user,"Paris"))  # {'name':'Ada','address':{'city':'Paris'}}
```

---

## 10. Agents and Plans

Compose agents as categorical functors.

```python
from lambdacat.agents.plan import Sequence, Plan
from lambdacat.agents.runtime import strong_monoidal_functor

plan = Sequence([
    Plan.primitive("greet", lambda s: s+["hi"]),
    Plan.primitive("ask", lambda s: s+["how are you?"]),
])
agent = strong_monoidal_functor(plan)

print(agent([]))  # ['hi','how are you?']
```

---

## 11. Realistic Examples

### Data pipeline
- Objects = stages
- Morphisms = transforms
- Diagrams show flows

### Game model
- Objects = player states
- Morphisms = moves
- Category encodes all possible transitions

### AI agent
- Writer monad for logs
- State monad for memory
- Result monad for failures
- Kleisli category composes decisions

---

## 12. Where to Go Next

- Use LambdaCat for **small models, teaching, FP workflows, agent prototypes**.  
- Use HyperCat for **higher categories, homotopy, serious research proofs**.  

---

LambdaCat is your **entry point**: it makes category theory tangible in Python, with laws and diagrams you can run and check.
