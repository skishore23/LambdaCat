from __future__ import annotations

from typing import Callable, Generic, Protocol, TypeVar


A = TypeVar("A")
B = TypeVar("B")


class FunctorT(Protocol, Generic[A]):
	"""FP Functor typeclass.

	Implementations must provide an instance method `map` that applies a pure
	function to the contained value, returning a new functor value.
	"""

	def map(self, f: Callable[[A], B]) -> "FunctorT[B]": ...


class ApplicativeT(FunctorT[A], Protocol, Generic[A]):
	"""FP Applicative typeclass.

	Requires a `pure` constructor and function application `ap`.
	`ap` applies a function inside the context to the value in this context.
	"""

	@classmethod
	def pure(cls, x: A) -> "ApplicativeT[A]": ...

	def ap(self, ff: "ApplicativeT[Callable[[A], B]]") -> "ApplicativeT[B]": ...


class MonadT(ApplicativeT[A], Protocol, Generic[A]):
	"""FP Monad typeclass.

	Requires `bind` (aka `flatMap`).
	"""

	def bind(self, f: Callable[[A], "MonadT[B]"]) -> "MonadT[B]": ...


def fmap(m: MonadT[A], f: Callable[[A], B]) -> MonadT[B]:
	"""Map a pure function over a monadic value using bind/pure.

	Fail-fast if the instance does not satisfy the required interface at runtime.
	This helper is defined in terms of `bind` and `pure` to emphasize minimal
	requirements.
	"""

	if not hasattr(m, "bind"):
		raise TypeError("fmap requires a monad with a 'bind' method")
	cls = type(m)
	if not hasattr(cls, "pure"):
		raise TypeError("fmap requires a monad class with a 'pure' classmethod")
	return m.bind(lambda a: cls.pure(f(a)))


