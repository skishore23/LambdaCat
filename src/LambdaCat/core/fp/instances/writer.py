from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Tuple, TypeVar

from ..typeclasses import Monoid


W = TypeVar("W")
A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Writer(Generic[W, A]):
	"""Writer monad: accumulate logs W alongside value A.

	Requires a Monoid[W] instance to combine logs. We thread a `monoid` value
	inside the instance to preserve purity and avoid globals.
	"""

	value: A
	log: W
	monoid: Monoid[W]

	@classmethod
	def pure(cls, x: A, monoid: Monoid[W]) -> "Writer[W, A]":
		return Writer(x, monoid.empty(), monoid)

	def map(self, f: Callable[[A], B]) -> "Writer[W, B]":
		return Writer(f(self.value), self.log, self.monoid)

	def ap(self, ff: "Writer[W, Callable[[A], B]]") -> "Writer[W, B]":
		combined = self.monoid.combine(ff.log, self.log)
		return Writer(ff.value(self.value), combined, self.monoid)

	def bind(self, f: Callable[[A], "Writer[W, B]"]) -> "Writer[W, B]":
		next_w = f(self.value)
		combined = self.monoid.combine(self.log, next_w.log)
		if next_w.monoid is not self.monoid:
			raise TypeError("Writer.bind requires the same Monoid instance for combination")
		return Writer(next_w.value, combined, self.monoid)

	def tell(self, w: W) -> "Writer[W, A]":
		return Writer(self.value, self.monoid.combine(self.log, w), self.monoid)


