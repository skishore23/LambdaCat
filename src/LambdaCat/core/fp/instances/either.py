from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar, Union


L = TypeVar("L")
A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Either(Generic[L, A]):
	"""Minimal Either monad.

	Invariant: exactly one of `left` or `right` is not None.
	- `Left(e)` represents failure with error value `e`
	- `Right(a)` represents success with value `a`
	"""

	left: Optional[L]
	right: Optional[A]

	def __post_init__(self) -> None:
		if (self.left is None) == (self.right is None):
			raise ValueError("Either must have exactly one of (left, right) set")

	@classmethod
	def left_value(cls, e: L) -> "Either[L, A]":
		return Either(left=e, right=None)

	@classmethod
	def right_value(cls, a: A) -> "Either[L, A]":
		return Either(left=None, right=a)

	# Applicative.pure: embed value as Right
	@classmethod
	def pure(cls, x: A) -> "Either[L, A]":
		return Either(left=None, right=x)

	# Functor.map: map over Right only
	def map(self, f: Callable[[A], B]) -> "Either[L, B]":
		if self.right is None:
			return Either(left=self.left, right=None)  # Left flows through
		return Either(left=None, right=f(self.right))

	# Applicative.ap: apply Right(function) to Right(value); propagate Left otherwise
	def ap(self, ff: "Either[L, Callable[[A], B]]") -> "Either[L, B]":
		if self.left is not None:
			return Either(left=self.left, right=None)
		if ff.left is not None:
			return Either(left=ff.left, right=None)
		assert self.right is not None and ff.right is not None  # by invariants above
		return Either(left=None, right=ff.right(self.right))

	# Monad.bind: if Right(a), apply f(a); if Left, propagate
	def bind(self, f: Callable[[A], "Either[L, B]"]) -> "Either[L, B]":
		if self.right is None:
			return Either(left=self.left, right=None)
		return f(self.right)


