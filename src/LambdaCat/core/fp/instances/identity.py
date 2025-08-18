from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Id(Generic[A]):
	value: A

	@classmethod
	def pure(cls, x: A) -> "Id[A]":
		return Id(x)

	def map(self, f: Callable[[A], B]) -> "Id[B]":
		return Id(f(self.value))

	def ap(self, ff: "Id[Callable[[A], B]]") -> "Id[B]":
		return Id(ff.value(self.value))

	def bind(self, f: Callable[[A], "Id[B]"]) -> "Id[B]":
		return f(self.value)


