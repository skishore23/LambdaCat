from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


R = TypeVar("R")
A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Reader(Generic[R, A]):
	"""Reader monad: environment R threaded read-only.

	Model as a single field `run: R -> A`.
	"""

	run: Callable[[R], A]

	@classmethod
	def pure(cls, x: A) -> "Reader[R, A]":
		return Reader(lambda _r: x)

	def map(self, f: Callable[[A], B]) -> "Reader[R, B]":
		return Reader(lambda r: f(self.run(r)))

	def ap(self, ff: "Reader[R, Callable[[A], B]]") -> "Reader[R, B]":
		return Reader(lambda r: ff.run(r)(self.run(r)))

	def bind(self, f: Callable[[A], "Reader[R, B]"]) -> "Reader[R, B]":
		return Reader(lambda r: f(self.run(r)).run(r))


