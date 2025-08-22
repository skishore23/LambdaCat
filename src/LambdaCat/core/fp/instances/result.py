from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, cast

A = TypeVar("A")
B = TypeVar("B")
E = TypeVar("E")


class Result(Generic[A, E]):
    """Result monad, modeled as a closed sum type.

    Use `Result.ok(value)` and `Result.err(error)` to construct values.
    """

    # Factories
    @classmethod
    def ok(cls, value: A) -> "Result[A, E]":
        return Ok(value)

    @classmethod
    def err(cls, error: E) -> "Result[A, E]":
        return Err(error)

    @classmethod
    def pure(cls, value: A) -> "Result[A, E]":
        return cls.ok(value)

    def map(self, f: Callable[[A], B]) -> "Result[B, E]":  # pragma: no cover - abstract behavior
        raise NotImplementedError

    def ap(self, other: "Result[A, E]") -> "Result[B, E]":  # pragma: no cover - abstract behavior
        raise NotImplementedError

    def bind(self, f: Callable[[A], "Result[B, E]"]) -> "Result[B, E]":  # pragma: no cover
        raise NotImplementedError

    def map_error(self, f: Callable[[E], E]) -> "Result[A, E]":  # pragma: no cover - abstract
        raise NotImplementedError

    # Type guards and helpers
    def is_ok(self) -> bool:
        return isinstance(self, Ok)

    def is_err(self) -> bool:
        return isinstance(self, Err)

    def get_or_else(self: "Result[A, E]", default: A) -> A:
        if isinstance(self, Ok):
            ok_self = cast(Ok[A, E], self)
            return ok_self.value
        return default


@dataclass(frozen=True)
class Ok(Result[A, E]):
    value: A

    def map(self, f: Callable[[A], B]) -> "Result[B, E]":
        return Ok(f(self.value))

    def ap(self: "Ok[Callable[[A], B], E]", other: "Result[A, E]") -> "Result[B, E]":
        if isinstance(other, Err):
            return Err(other.error)
        if isinstance(other, Ok):
            # self.value is a Callable[[A], B] due to self type on ap
            return Ok(self.value(other.value))
        # Safety: all Result instances are Ok or Err
        raise AssertionError("Unreachable state for Result.ap")

    def bind(self, f: Callable[[A], "Result[B, E]"]) -> "Result[B, E]":
        return f(self.value)

    def map_error(self, f: Callable[[E], E]) -> "Result[A, E]":
        return self

    def __repr__(self) -> str:
        return f"Result.ok({self.value})"


@dataclass(frozen=True)
class Err(Result[A, E]):
    error: E

    def map(self, f: Callable[[A], B]) -> "Result[B, E]":
        return Err(self.error)

    def ap(self, other: "Result[A, E]") -> "Result[B, E]":
        return Err(self.error)

    def bind(self, f: Callable[[A], "Result[B, E]"]) -> "Result[B, E]":
        return Err(self.error)

    def map_error(self, f: Callable[[E], E]) -> "Result[A, E]":
        return Err(f(self.error))

    def __repr__(self) -> str:
        return f"Result.err({self.error})"
