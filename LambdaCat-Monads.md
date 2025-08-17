# Monads (and All That Jazz) for LambdaCat

## Why Monads?
LambdaCat already has **Functors**. Functional programmers will expect the full trio:
- **Functor**
- **Applicative**
- **Monad**

together with **law checkers**, **instances**, and a **Kleisli category**.  
This makes LambdaCat instantly familiar to FP developers and provides categorical rigor.

---

## Goals
1. **Typeclass trio:** `Functor`, `Applicative`, `Monad` with **law suites**.  
2. **Core instances:** `Identity`, `Maybe/Option`, `Either`, `Reader`, `Writer`, `State`, `List`.  
3. **Kleisli category:** build `Kl(M)` for any monad `M`.  
4. **Do-notation ergonomics:** Pythonic helpers for sequencing.  
5. **Transformers or Free monad:** minimal, practical effect layering.  
6. **Property tests:** Hypothesis-based checkers for Functor/Applicative/Monad laws.

---

## Minimal API Sketch

```python
# lambdacat/monads/core.py
from typing import Callable, Generic, TypeVar, Protocol

A = TypeVar("A"); B = TypeVar("B")

class Functor(Protocol, Generic[A]):
    def map(self, f: Callable[[A], B]) -> "Functor[B]": ...

class Applicative(Functor[A], Protocol, Generic[A]):
    @classmethod
    def pure(cls, x: A) -> "Applicative[A]": ...
    def ap(self, ff: "Applicative[Callable[[A], B]]") -> "Applicative[B]": ...

class Monad(Applicative[A], Protocol, Generic[A]):
    def bind(self, f: Callable[[A], "Monad[B]"]) -> "Monad[B]": ...
    def fmap(self, f: Callable[[A], B]) -> "Monad[B]":
        return self.bind(lambda a: type(self).pure(f(a)))
```

---

## Core Instances

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Id(Generic[A]):
    value: A
    @classmethod
    def pure(cls, x: A) -> "Id[A]": return Id(x)
    def map(self, f): return Id(f(self.value))
    def ap(self, ff): return Id(ff.value(self.value))
    def bind(self, f): return f(self.value)

@dataclass(frozen=True)
class Maybe(Generic[A]):
    value: A | None
    @classmethod
    def pure(cls, x: A) -> "Maybe[A]": return Maybe(x)
    def map(self, f): return Maybe(None) if self.value is None else Maybe(f(self.value))
    def ap(self, ff):
        return Maybe(None) if self.value is None or ff.value is None else Maybe(ff.value(self.value))
    def bind(self, f): return Maybe(None) if self.value is None else f(self.value)
```

(Either, Reader, Writer, State, List are similar.)

---

## Law Suites

```python
# lambdacat/monads/laws.py
def functor_laws(F_cls, gen):
    # fmap id == id
    # fmap (g ∘ f) == fmap g ∘ fmap f

def monad_laws(M_cls, gen):
    # Left identity: pure a >>= k == k a
    # Right identity: m >>= pure == m
    # Associativity: (m >>= k) >>= h == m >>= (λa. k a >>= h)
```

Use **Hypothesis** generators for property-based tests. Integrate with LambdaCat’s `LawSuite`.

---

## Kleisli Category

```python
class Kleisli(Generic[A,B]):
    def __init__(self, run, M):
        self.run, self.M = run, M

    def then(self, g: "Kleisli[B,C]") -> "Kleisli[A,C]":
        return Kleisli(lambda a: self.run(a).bind(g.run), self.M)

    @classmethod
    def id(cls, M):
        return Kleisli(lambda a: M.pure(a), M)
```

- Objects: types (or finite state sets).  
- Morphisms: `A -> M B`.  
- Composition: `bind`.  
- Identity: `pure`.  
- Plug into `Cat` for law-checking.

---

## Agents with Effects

Define primitives as **Kleisli arrows** in a monad.

### Example 1: State Monad
```python
def get(): return State(lambda s: (s, s))
def put(ns): return State(lambda s: (None, ns))

inc = Kleisli(lambda _: get().bind(lambda n: put(n+1).bind(lambda _: State.pure(None))), State)
double = Kleisli(lambda _: get().bind(lambda n: put(2*n).bind(lambda _: State.pure(None))), State)

plan = inc.then(double).then(inc)
_, s_final = plan.run(None).run(0) # s_final == 3
```

### Example 2: Writer Monad
```python
log = Kleisli(lambda msg: Writer.pure(None).tell([msg]), Writer)
agent = log.then(log).then(log)  # 3 logs
```

---

## All That Jazz

1. **Applicatives** for parallel composition (`zipA`).  
2. **Monad Transformers or Free Monad** for stacking effects.  
   - *Free* is best for agent DSLs (separate spec vs execution).  
3. **Do-notation** helper (`@do` decorator).  
4. **Law-driven docs/examples** (logging, config, nondeterminism, parsers).

---

## Roadmap

**Phase 1**:  
- Implement `Applicative`, `Monad`.  
- Add `Id`, `Maybe`, `Either`, `Reader`, `Writer`, `State`, `List`.  
- Law suites.

**Phase 2**:  
- `kleisli_cat(M, Obj)` wrapper.  
- Plan→Kleisli compiler with `mode={"applicative","monadic"}`.  

**Phase 3**:  
- Do-notation helpers.  
- Cookbook demos.  

**Phase 4**:  
- Free monad for agent DSL or transformers.  

**Phase 5**:  
- Bridge `Kl(M)` → HyperCat for heavy commutativity/proofs.

---

## Summary
- Monads make LambdaCat **immediately appealing to functional programmers**.  
- Provides a principled way to encode **effects, agents, and composition**.  
- With law suites and Kleisli categories, LambdaCat stays **theoretically consistent** and **practically useful**.  
