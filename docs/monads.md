# LambdaCat FP Monads Plan (RFC)

## Motivation

LambdaCat already models categories, functors, and natural transformations. Adding the FP trio — Functor, Applicative, Monad — and the Kleisli construction makes effectful composition first-class and law-driven.

- Predictable composition: laws constrain implementations and catch bugs.
- Effects as morphisms: Kleisli turns arrows `A -> M B` into a category compatible with `Cat` and existing law suites.
- Ergonomics: Applicative for independent/parallel composition; Monad for dependent/sequential composition.

## Scope

- Typeclasses: FP-style `Functor`, `Applicative`, `Monad` as Protocols (no clash with categorical `Functor`).
- Instances: `Id`, `Maybe` (Phase 1). `Either`, `Reader`, `Writer`, `State`, `ListM` (Phase 3).
- Law suites: Functor/Applicative/Monad laws using existing `LawSuite` engine (Phase 1).
- Kleisli: Build `Kl(M)` as a `Cat` for any `Monad` (Phase 4).
- Do-notation helper (Phase 5, optional).

Out of scope for initial phases: transformers/free monad; heavy dependencies; runtime magic.

## Design Overview

- Keep categorical core unchanged under `src/LambdaCat/core/`.
- Introduce FP constructs under `src/LambdaCat/core/fp/` to avoid name clashes and preserve modularity.
- Raise explicit exceptions on invalid states; no silent fallbacks.
- Strong typing: mypy --strict, explicit generics; avoid Any except at Protocol boundaries.

### Module Layout

- `src/LambdaCat/core/fp/typeclasses.py`
  - Protocols: `FunctorT[A]`, `ApplicativeT[A]`, `MonadT[A]`.
  - Small helpers: `fmap(monad_like, f)` (implemented via `bind`/`pure`).
- `src/LambdaCat/core/fp/instances/identity.py`
  - `Id[A]`: `pure`, `map`, `ap`, `bind`.
- `src/LambdaCat/core/fp/instances/maybe.py`
  - `Maybe[A]` with `None` representing failure; `pure`, `map`, `ap`, `bind`.
- `src/LambdaCat/core/fp/laws.py`
  - Functor laws (identity, composition).
  - Applicative laws (identity, homomorphism, interchange, composition).
  - Monad laws (left/right identity, associativity).
- `src/LambdaCat/core/fp/kleisli.py`
  - Builder for `Kl(M)` as a `Cat` using monadic composition.
- `src/LambdaCat/core/fp/do.py` (optional)
  - Minimal helper for sequencing monadic code ergonomically.
- `src/LambdaCat/core/fp/__init__.py`
  - Thin re-exports; no heavy imports.

No imports from `extras/` or `plugins/` in core.

## APIs (precise; strongly typed)

```python
# src/LambdaCat/core/fp/typeclasses.py
from typing import Callable, Generic, Protocol, TypeVar

A = TypeVar("A"); B = TypeVar("B")

class FunctorT(Protocol, Generic[A]):
    def map(self, f: Callable[[A], B]) -> "FunctorT[B]": ...

class ApplicativeT(FunctorT[A], Protocol, Generic[A]):
    @classmethod
    def pure(cls, x: A) -> "ApplicativeT[A]": ...
    def ap(self, ff: "ApplicativeT[Callable[[A], B]]") -> "ApplicativeT[B]": ...

class MonadT(ApplicativeT[A], Protocol, Generic[A]):
    def bind(self, f: Callable[[A], "MonadT[B]"]) -> "MonadT[B]": ...

# Helper built in terms of bind/pure; raises if required methods are missing
def fmap(m: MonadT[A], f: Callable[[A], B]) -> MonadT[B]:
    return m.bind(lambda a: type(m).pure(f(a)))
```

### Instances (Phase 1)

```python
# src/LambdaCat/core/fp/instances/identity.py
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

A = TypeVar("A"); B = TypeVar("B")

@dataclass(frozen=True)
class Id(Generic[A]):
    value: A
    @classmethod
    def pure(cls, x: A) -> "Id[A]": return Id(x)
    def map(self, f: Callable[[A], B]) -> "Id[B]": return Id(f(self.value))
    def ap(self, ff: "Id[Callable[[A], B]]") -> "Id[B]": return Id(ff.value(self.value))
    def bind(self, f: Callable[[A], "Id[B]"]) -> "Id[B]": return f(self.value)
```

```python
# src/LambdaCat/core/fp/instances/maybe.py
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

A = TypeVar("A"); B = TypeVar("B")

@dataclass(frozen=True)
class Maybe(Generic[A]):
    value: Optional[A]
    @classmethod
    def pure(cls, x: A) -> "Maybe[A]": return Maybe(x)
    def map(self, f: Callable[[A], B]) -> "Maybe[B]":
        return Maybe(None) if self.value is None else Maybe(f(self.value))
    def ap(self, ff: "Maybe[Callable[[A], B]]") -> "Maybe[B]":
        if self.value is None or ff.value is None: return Maybe(None)
        return Maybe(ff.value(self.value))
    def bind(self, f: Callable[[A], "Maybe[B]"]) -> "Maybe[B]":
        return Maybe(None) if self.value is None else f(self.value)
```

### Kleisli Category

- Objects: names of types/states (strings).
- Morphisms: named arrows with semantics `A -> M B` (Python callables returning `MonadT`).
- Composition: `(g ∘ f)(a) = f(a).bind(g)`.
- Identity on `A`: `lambda a: M.pure(a)`.
- Build a `Cat` using existing `Presentation`/`Cat` data model and validate with `CATEGORY_SUITE`.

## Laws

- Implement as `Law` instances within `src/LambdaCat/core/fp/laws.py`, using existing `LawSuite` runner.
- No random I/O; property tests pass generators via config or Hypothesis strategies in tests.

Functor laws:
- `map(id) == id`
- `map(g ∘ f) == map(g) ∘ map(f)`

Applicative laws:
- identity, homomorphism, interchange, composition

Monad laws:
- left identity, right identity, associativity

## Tests

- `tests/test_fp_functor.py`: Functor laws for `Id`, `Maybe`.
- `tests/test_fp_applicative.py`: Applicative laws for `Id`, `Maybe`.
- `tests/test_fp_monad.py`: Monad laws for `Id`, `Maybe`.
- `tests/test_kleisli.py`: `Kl(M)` satisfies category identities/associativity via `CATEGORY_SUITE` on finite examples.

Use Hypothesis for property tests; keep strategies small and deterministic where possible to avoid flaky CI.

## Integration Notes

- Do not modify `core/functor.py` (categorical functors). FP constructs live under `core/fp/`.
- No imports from `extras/` or `plugins/` inside `core/fp/`.
- Thin re-exports from `src/LambdaCat/core/__init__.py` are optional; prefer keeping `fp` namespaced.

## Phases and Deliverables

- Phase 1
  - Files: `typeclasses.py`, `instances/identity.py`, `instances/maybe.py`, `laws.py`.
  - Tests: functor/applicative/monad laws for Id/Maybe.
- Phase 2
  - `kleisli.py` and tests integrating with `CATEGORY_SUITE`.
- Phase 3
  - Instances: `Either`, `Reader`, `Writer` (with `Monoid` Protocol for `W`), `State`, `ListM`.
  - Expand tests and law coverage.
- Phase 4
  - Optional `do.py` helper and docs/examples.

Each phase must pass: ruff, mypy --strict, pytest suites.

## Acceptance Criteria

- Strong typing: no Any in public APIs; Protocols define exact shapes.
- Fail-fast: explicit exceptions on invalid states; no silent fallbacks.
- Law-sound: all law suites pass for included instances.
- Category integration: `Kl(M)` categories satisfy `CATEGORY_SUITE`.
- Isolation: no cross-imports from `extras/`/`plugins/` into core.

## Risks / Mitigations

- Name collision with categorical `Functor`: avoid by `core/fp/` namespacing and `*T` suffix.
- Overreach in first PR: phase deliverables are small and independently valuable.
- Property-test flakiness: control strategy sizes; cap Hypothesis settings in CI.