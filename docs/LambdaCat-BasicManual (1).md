# LambdaCat Basic Manual

LambdaCat is a **Python toolkit for categories, functors, and functional programming patterns**.  
It is designed to be:
- **Pedagogical**: a learning and teaching tool for category theory.  
- **Practical**: usable for building FP-style programs and lightweight agents.  
- **Law-driven**: all structures come with **law suites** to verify correctness.  

---

## 1. Categories in LambdaCat

### 1.1 What is a Category?
A **category** consists of:
- A collection of **objects**.  
- A collection of **morphisms** (arrows) between objects.  
- A **composition law** for morphisms.  
- An **identity morphism** for every object.  

These data must satisfy:
- **Associativity**: (f∘g)∘h = f∘(g∘h).  
- **Identity**: id∘f = f = f∘id.  

LambdaCat makes these concepts **concrete** by representing objects as names (strings) and morphisms as explicitly listed arrows.

---

### 1.2 Defining a Category
You can build a category explicitly:

```python
from lambdacat.core.category import Cat

objects = ["A", "B", "C"]
morphisms = {
    ("A","A"): ["id_A"],
    ("B","B"): ["id_B"],
    ("C","C"): ["id_C"],
    ("A","B"): ["f"],
    ("B","C"): ["g"],
    ("A","C"): ["gf"],
}
composition = {
    ("f","g"): "gf"
}
identities = {"A":"id_A","B":"id_B","C":"id_C"}

C = Cat(objects, morphisms, composition, identities)
```

---

### 1.3 Standard Categories
LambdaCat provides canonical categories for reuse:

```python
from lambdacat.categories.standard import terminal_category, discrete_category, delta_category, walking_isomorphism

T = terminal_category()
D = discrete_category(["x","y"])
Delta3 = delta_category(3)
W = walking_isomorphism()
```

---

### 1.4 What Can You Do With a Category?

Once defined, categories are more than just containers — you can **use** them:

1. **Explore the structure**:
```python
print(C.objects)
print(C.morphisms)
print(C.identities)
```

2. **Draw diagrams**:
```python
from lambdacat.render import mermaid
print(mermaid(C))
```

3. **Check commutativity**:
```python
from lambdacat.lawsuite import check_commutativity
paths = [["f","g"], ["h","k"]]
print(check_commutativity(C, "A","D", paths))
```

4. **Test categorical laws**:
```python
from lambdacat.lawsuite import CATEGORY_SUITE
CATEGORY_SUITE.run_suite(C)
```

5. **Build functors from it**:
```python
from lambdacat.core.functor import FunctorBuilder
F = FunctorBuilder(C, C)
F.add_object_mapping("A","B")
F.add_morphism_mapping("f","g")
functor = F.build()
```

6. **Check universal properties** (where implemented):
```python
from lambdacat.props import has_terminal, is_iso
print(has_terminal(C))
print(is_iso(C,"f"))
```

7. **Compose with other structures**:
- Opposite category `C.op()`
- Slice categories
- Kleisli categories from monads

---

## 2. Functors and Natural Transformations

### 2.1 Functors
A **functor** maps:
- Objects to objects.  
- Morphisms to morphisms.  

It must preserve identities and composition.  

```python
from lambdacat.core.functor import FunctorBuilder

F = FunctorBuilder(C, C)
F.add_object_mapping("A","B")
F.add_morphism_mapping("f","g")
functor = F.build()
```

---

### 2.2 Natural Transformations
Given two functors `F, G: C → D`, a natural transformation `η` assigns to each object X in C a morphism:

```
η_X: F(X) → G(X)
```

such that for every f: X → Y:

```
η_Y ∘ F(f) = G(f) ∘ η_X
```

LambdaCat provides `check_naturality`:

```python
from lambdacat.core.natural import check_naturality
check_naturality(F, G, eta)
```

---

## 3. Laws and Their Importance

### 3.1 Why Laws?
In mathematics, categories and functors are defined by axioms.  
LambdaCat encodes these axioms as **laws** you can automatically test.  

This ensures that your structures are **not just data**, but valid categorical objects.

---

### 3.2 Category Laws
- Associativity
- Identity

```python
from lambdacat.lawsuite import CATEGORY_SUITE
CATEGORY_SUITE.run_suite(C)
```

---

### 3.3 Functor Laws
- Preservation of identity  
- Preservation of composition  

---

### 3.4 Monad Laws
- Left identity  
- Right identity  
- Associativity  

```python
from lambdacat.monads.instances import Maybe
from lambdacat.monads.laws import monad_laws

monad_laws(Maybe, gen=lambda: Maybe.pure(1))
```

---

## 4. From Functors to Monads

### 4.1 Functors
- Minimal notion: ability to **map** a function over a context.  
```python
from lambdacat.data import Option
print(Option.some(3).map(lambda x: x+1))  # Some(4)
```

Laws:
- F(id) = id
- F(g∘f) = F(g)∘F(f)

---

### 4.2 Applicatives
- Extend functors with the ability to apply **wrapped functions**.  
```python
add = Option.pure(lambda x,y: x+y)
print(add.ap(Option.some(2)).ap(Option.some(3)))  # Some(5)
```

Laws:
- Identity
- Homomorphism
- Interchange
- Composition

---

### 4.3 Monads
- Extend applicatives with **bind**: sequencing computations where the next step depends on the previous result.  
```python
from lambdacat.data import Result

safe_div = lambda x,y: Result.err("div by zero") if y==0 else Result.ok(x/y)
print(Result.ok((10,2)).bind(lambda xy: safe_div(*xy)))  # Ok(5.0)
```

Laws:
- Left identity
- Right identity
- Associativity

---

### 4.4 The Chain
Every monad is also an applicative, and every applicative is also a functor.

```
Functor ⊂ Applicative ⊂ Monad
```

LambdaCat provides **law suites** for each layer, so you can verify correctness at all levels.

---

## 5. Functional Programming in LambdaCat

### 5.1 Option and Result
```python
from lambdacat.data import Option, Result

x = Option.some(42)
y = Option.none()
print(x.map(lambda n: n + 1))   # Some(43)
print(y.map(lambda n: n + 1))   # None
```

---

### 5.2 State Monad and Kleisli
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

## 6. Optics

### 6.1 Lenses
```python
from lambdacat.optics import lens

user = {"name":"Ada","address":{"city":"London"}}
city_lens = lens["address"]["city"]

print(city_lens.get(user)) # London
print(city_lens.set(user,"Paris"))
```

---

### 6.2 Prisms
Prisms let you work with sum types (`Option`, `Result`) safely.

---

## 7. Agents and Plans

LambdaCat includes a DSL for **agents** built from composable plans.

```python
from lambdacat.agents.plan import Sequence, Plan
from lambdacat.agents.runtime import strong_monoidal_functor

plan = Sequence([
    Plan.primitive("greet", lambda s: s+["hi"]),
    Plan.primitive("farewell", lambda s: s+["bye"]),
])
agent = strong_monoidal_functor(plan)
print(agent([]))  # ['hi','bye']
```

---

## 8. Cookbook
- Logging with Writer  
- Config with Reader  
- Error handling with Result  
- State machines with State  
- Parallel validation with Applicative  
- Nondeterministic search with List  
- Parsing with Parser combinators  
- Immutable data updates with Lenses  
- Diagram commutativity checks  
- Kleisli agents with effects  

---

## 9. Philosophy
- **Law-first**: categorical correctness is enforced by testable laws.  
- **Composable**: complex systems built from small categorical parts.  
- **Bridging worlds**: Python FP + category theory; HyperCat integration for higher categories.  

---
