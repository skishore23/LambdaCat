from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Protocol, TypeVar

A = TypeVar("A")


class Semigroup(Protocol[A]):
    """Semigroup typeclass - associative binary operation."""

    def combine(self, left: A, right: A) -> A:
        """Associative binary operation."""
        ...


@dataclass(frozen=True)
class StringSemigroup:
    """String concatenation semigroup."""

    def combine(self, left: str, right: str) -> str:
        return left + right


@dataclass(frozen=True)
class ListSemigroup(Generic[A]):
    """List concatenation semigroup."""

    def combine(self, left: list[A], right: list[A]) -> list[A]:
        return left + right


@dataclass(frozen=True)
class IntAddSemigroup:
    """Integer addition semigroup."""

    def combine(self, left: int, right: int) -> int:
        return left + right


@dataclass(frozen=True)
class IntMulSemigroup:
    """Integer multiplication semigroup."""

    def combine(self, left: int, right: int) -> int:
        return left * right


@dataclass(frozen=True)
class FunctionSemigroup(Generic[A]):
    """Function composition semigroup."""

    def combine(self, left: Callable[[A], A], right: Callable[[A], A]) -> Callable[[A], A]:
        return lambda x: left(right(x))
