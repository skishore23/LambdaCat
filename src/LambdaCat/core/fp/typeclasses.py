from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar, cast

A = TypeVar("A")
B = TypeVar("B")
W = TypeVar("W")


class FunctorT(ABC, Generic[A]):
	"""FP Functor typeclass.

	Implementations must provide an instance method `map` that applies a pure
	function to the contained value, returning a new functor value.
	"""

	@abstractmethod
	def map(self, f: Callable[[A], B]) -> FunctorT[B]: ...


class ApplicativeT(FunctorT[A], ABC, Generic[A]):
	"""FP Applicative typeclass.

	Requires a `pure` constructor and function application `ap`.
	`ap` applies a function inside the context to the value in this context.
	"""

	@classmethod
	@abstractmethod
	def pure(cls, x: A) -> ApplicativeT[A]: ...

	@abstractmethod
	def ap(self: ApplicativeT[Callable[[A], B]], fa: ApplicativeT[A]) -> ApplicativeT[B]: ...


class MonadT(ApplicativeT[A], ABC, Generic[A]):
	"""FP Monad typeclass.

	Requires `bind` (aka `flatMap`).
	"""

	@abstractmethod
	def bind(self, f: Callable[[A], MonadT[B]]) -> MonadT[B]: ...


def fmap(m: MonadT[A], f: Callable[[A], B]) -> MonadT[B]:
	"""Map a pure function over a monadic value using bind/pure.

	This helper is defined in terms of `bind` and `pure` to emphasize minimal
	requirements.
	"""

	if not hasattr(m, "bind"):
		raise TypeError("fmap requires a monad with a 'bind' method")
	cls = type(m)
	if not hasattr(cls, "pure"):
		raise TypeError("fmap requires a monad class with a 'pure' classmethod")

	# Type-safe implementation using monad's map method instead of bind/pure
	# This avoids the type inference issue
	if hasattr(m, "map"):
		return cast(MonadT[B], m.map(f))
	else:
		# Fallback to bind/pure implementation
		return cast(MonadT[B], m.bind(lambda a: cast(type[MonadT[B]], cls).pure(f(a))))


class Semigroup(ABC, Generic[W]):
	"""Semigroup protocol for associative operations.

	Implementations must provide an associative combine operation.
	"""

	@abstractmethod
	def combine(self, left: W, right: W) -> W: ...


class Monoid(Semigroup[W], ABC, Generic[W]):
	"""Monoid protocol for Writer logs and similar structures.

	Implementations must provide an identity element and an associative combine.
	Extends Semigroup with an identity element.
	"""

	@abstractmethod
	def empty(self) -> W: ...


