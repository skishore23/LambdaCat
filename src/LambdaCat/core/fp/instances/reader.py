from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

A = TypeVar("A")
B = TypeVar("B")
R = TypeVar("R")


@dataclass(frozen=True)
class Reader(Generic[R, A]):
    """Reader monad for dependency injection."""

    run: Callable[[R], A]

    @classmethod
    def pure(cls, value: A) -> Reader[R, A]:
        return cls(lambda _: value)

    def map(self, f: Callable[[A], B]) -> Reader[R, B]:
        return Reader(lambda r: f(self.run(r)))

    def ap(self: Reader[R, Callable[[A], B]], ra: Reader[R, A]) -> Reader[R, B]:
        """Apply function from this Reader to the value in ra (function.ap(value))."""
        return Reader(lambda r: self.run(r)(ra.run(r)))

    def bind(self, f: Callable[[A], Reader[R, B]]) -> Reader[R, B]:
        return Reader(lambda r: f(self.run(r)).run(r))

    def local(self, g: Callable[[R], R]) -> Reader[R, A]:
        return Reader(lambda r: self.run(g(r)))

    def __call__(self, r: R) -> A:
        return self.run(r)


