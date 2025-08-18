# FP Monads (Functor, Applicative, Monad)


## Design principles
- Functional and composable: tiny pure dataclasses; orchestration outside core
- Fail-fast: invalid states raise; no placeholders
- Strong typing: protocols and frozen dataclasses; mypy --strict friendly
- Law-centric: small suites validate critical identities

## Modules
- `typeclasses.py`: `FunctorT`, `ApplicativeT`, `MonadT`, and `fmap(m, f)`
- `instances/identity.py`: `Id[A]`
- `instances/maybe.py`: `Maybe[A]` (None as failure)
- `instances/either.py`: `Either[L, A]` (Left/Right)
- `instances/reader.py`: `Reader[R, A]` (read-only env)
- `instances/writer.py`: `Writer[W, A]` (accumulating logs via `Monoid[W]`)
- `instances/state.py`: `State[S, A]` (state threading)
- `kleisli.py`: `Kleisli[A,B]` for monadic arrows and `kleisli_identity(pure)`
- `laws.py`: minimal law suites (Functor/Applicative identity, Monad right identity)
- `__init__.py`: thin re-exports

## APIs

```python
# typeclasses.py
from typing import Callable, Protocol, TypeVar, Generic

A = TypeVar("A"); B = TypeVar("B")

class FunctorT(Protocol, Generic[A]):
    def map(self, f: Callable[[A], B]) -> "FunctorT[B]": ...

class ApplicativeT(FunctorT[A], Protocol, Generic[A]):
    @classmethod
    def pure(cls, x: A) -> "ApplicativeT[A]": ...
    def ap(self, ff: "ApplicativeT[Callable[[A], B]]") -> "ApplicativeT[B]": ...

class MonadT(ApplicativeT[A], Protocol, Generic[A]):
    def bind(self, f: Callable[[A], "MonadT[B]"]) -> "MonadT[B]": ...

def fmap(m: MonadT[A], f: Callable[[A], B]) -> MonadT[B]:
    return m.bind(lambda a: type(m).pure(f(a)))
```

### Instances

```python
# instances/identity.py
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
# instances/maybe.py
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

```python
# instances/either.py
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar
L = TypeVar("L"); A = TypeVar("A"); B = TypeVar("B")

@dataclass(frozen=True)
class Either(Generic[L, A]):
    left: Optional[L]
    right: Optional[A]
    def __post_init__(self) -> None:
        if (self.left is None) == (self.right is None):
            raise ValueError("Either must have exactly one of (left, right) set")
    @classmethod
    def left_value(cls, e: L) -> "Either[L, A]": return Either(left=e, right=None)
    @classmethod
    def right_value(cls, a: A) -> "Either[L, A]": return Either(left=None, right=a)
    @classmethod
    def pure(cls, x: A) -> "Either[L, A]": return Either(left=None, right=x)
    def map(self, f: Callable[[A], B]) -> "Either[L, B]":
        return self if self.right is None else Either(left=None, right=f(self.right))
    def ap(self, ff: "Either[L, Callable[[A], B]]") -> "Either[L, B]":
        if self.left is not None: return Either(left=self.left, right=None)
        if ff.left is not None: return Either(left=ff.left, right=None)
        assert self.right is not None and ff.right is not None
        return Either(left=None, right=ff.right(self.right))
    def bind(self, f: Callable[[A], "Either[L, B]"]) -> "Either[L, B]":
        return self if self.right is None else f(self.right)
```

### Kleisli

```python
# kleisli.py
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar
from .typeclasses import MonadT
A = TypeVar("A"); B = TypeVar("B"); C = TypeVar("C")

@dataclass(frozen=True)
class Kleisli(Generic[A, B]):
    run: Callable[[A], MonadT[B]]
    def then(self, g: "Kleisli[B, C]") -> "Kleisli[A, C]":
        return Kleisli(lambda a: self.run(a).bind(g.run))

def kleisli_identity(pure: Callable[[A], MonadT[A]]) -> Kleisli[A, A]:
    return Kleisli(lambda a: pure(a))

# Optional builder for a structural category of the Kleisli graph (names only)
def kleisli_category(name: str, objects: Tuple[str,...], morphisms: Mapping[str, Tuple[str,str]], compose_semantics: Mapping[Tuple[str,str], str]) -> Cat:
    ...
```

## Usage

- Functor map
```python
from LambdaCat.core.fp.instances.maybe import Maybe
Maybe(10).map(lambda n: n * 2)          # Maybe(20)
Maybe(None).map(lambda n: n * 2)        # Maybe(None)
```

- Applicative ap
```python
from LambdaCat.core.fp.instances.maybe import Maybe
add = lambda a: (lambda b: a + b)
Maybe(3).ap(Maybe.pure(lambda x: x + 1))   # Maybe(4)
Maybe(2).ap(Maybe.pure(add(5)))            # Maybe(7)
```

- Monad bind
```python
from LambdaCat.core.fp.instances.maybe import Maybe
def safe_div(a: int, b: int) -> Maybe[int]:
    return Maybe(None) if b == 0 else Maybe(a // b)
Maybe(100).bind(lambda n: safe_div(n, 2)).bind(lambda n: safe_div(n, 5))  # Maybe(10)
```

- Either for explicit errors
```python
from LambdaCat.core.fp.instances.either import Either
parse = lambda s: Either.left_value("bad") if not s.isdigit() else Either.right_value(int(s))
recip = lambda n: Either.left_value("zero") if n == 0 else Either.right_value(1.0 / n)
parse("42").bind(recip)  # Right(1/42)
```

- Kleisli composition
```python
from LambdaCat.core.fp.kleisli import Kleisli, kleisli_identity
from LambdaCat.core.fp.instances.maybe import Maybe

parse = Kleisli(lambda s: Maybe(int(s)) if s.isdigit() else Maybe(None))
recip = Kleisli(lambda n: Maybe(None) if n == 0 else Maybe(1.0 / n))
pipeline = parse.then(recip)
pipeline.run("12")   # Maybe(1/12)
pipeline.run("oops") # Maybe(None)
```

- Reader/Writer/State sketches
```python
from LambdaCat.core.fp.instances.reader import Reader
ask = Reader(lambda env: env)                  # A: read env
uppercase = Reader(lambda env: env.upper())    # map over env via Reader

from LambdaCat.core.fp.instances.writer import Writer
class ListMonoid:
    def empty(self): return []
    def combine(self, l, r): return l + r
W = ListMonoid()
Writer.pure(1, W).tell(["start"]).map(lambda x: x+1)  # value=2, log=["start"]

from LambdaCat.core.fp.instances.state import State
inc = State(lambda s: (None, s+1))
get = State(lambda s: (s, s))
program = get.bind(lambda n: State(lambda s: (n, s)))  # trivial pass-through
```

## Laws

Defined in `src/LambdaCat/core/fp/laws.py` and assembled into suites:
- Functor: Identity
- Applicative: Identity
- Monad: Right Identity

Additional properties are covered by tests in `tests/test_fp_*`.

## Notes
- FP constructs are isolated under `core/fp/`; categorical functors are in `core/functor.py`.
- No imports from `extras/` or `plugins/` inside core.