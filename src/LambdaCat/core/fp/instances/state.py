from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

A = TypeVar("A")
B = TypeVar("B")
S = TypeVar("S")


@dataclass(frozen=True)
class State(Generic[S, A]):
    """State monad for stateful computations."""

    run: Callable[[S], tuple[A, S]]

    @classmethod
    def pure(cls, value: A) -> State[S, A]:
        return cls(lambda s: (value, s))

    def map(self, f: Callable[[A], B]) -> State[S, B]:
        return State(lambda s: (f(self.run(s)[0]), self.run(s)[1]))

    def ap(self: State[S, Callable[[A], B]], sa: State[S, A]) -> State[S, B]:
        """Apply function from this State to the value in sa (function.ap(value))."""
        def run(s: S) -> tuple[B, S]:
            f, s1 = self.run(s)
            a, s2 = sa.run(s1)
            return f(a), s2
        return State(run)

    def bind(self, f: Callable[[A], State[S, B]]) -> State[S, B]:
        def run(s: S) -> tuple[B, S]:
            a, s1 = self.run(s)
            return f(a).run(s1)
        return State(run)

    @staticmethod
    def get() -> State[S, S]:
        return State(lambda s: (s, s))

    @staticmethod
    def put(new_state: S) -> State[S, None]:
        return State(lambda _: (None, new_state))

    @staticmethod
    def modify(f: Callable[[S], S]) -> State[S, None]:
        return State(lambda s: (None, f(s)))

    @staticmethod
    def gets(f: Callable[[S], A]) -> State[S, A]:
        return State(lambda s: (f(s), s))

    def __call__(self, s: S) -> tuple[A, S]:
        return self.run(s)


