from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar


A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Maybe(Generic[A]):
	value: Optional[A]

	@classmethod
	def pure(cls, x: A) -> "Maybe[A]":
		return Maybe(x)

	def map(self, f: Callable[[A], B]) -> "Maybe[B]":
		return Maybe(None) if self.value is None else Maybe(f(self.value))

	def ap(self, ff: "Maybe[Callable[[A], B]]") -> "Maybe[B]":
		if self.value is None or ff.value is None:
			return Maybe(None)
		return Maybe(ff.value(self.value))

	def bind(self, f: Callable[[A], "Maybe[B]"]) -> "Maybe[B]":
		return Maybe(None) if self.value is None else f(self.value)


