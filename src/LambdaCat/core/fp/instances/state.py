from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Tuple, TypeVar


S = TypeVar("S")
A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class State(Generic[S, A]):
	"""State monad: threads state S with value A.

	Represented as `run: S -> Tuple[A, S]`.
	"""

	run: Callable[[S], Tuple[A, S]]

	@classmethod
	def pure(cls, x: A) -> "State[S, A]":
		return State(lambda s: (x, s))

	def map(self, f: Callable[[A], B]) -> "State[S, B]":
		def step(s0: S) -> Tuple[B, S]:
			a, s1 = self.run(s0)
			return (f(a), s1)
		return State(step)

	def ap(self, ff: "State[S, Callable[[A], B]]") -> "State[S, B]":
		def step(s0: S) -> Tuple[B, S]:
			(f, s1) = ff.run(s0)
			(a, s2) = self.run(s1)
			return (f(a), s2)
		return State(step)

	def bind(self, f: Callable[[A], "State[S, B]"]) -> "State[S, B]":
		def step(s0: S) -> Tuple[B, S]:
			(a, s1) = self.run(s0)
			return f(a).run(s1)
		return State(step)


