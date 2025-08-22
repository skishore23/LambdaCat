from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ..typeclasses import FunctorT, ApplicativeT, MonadT

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Option(Generic[A]):
    """Option monad with fail-fast semantics."""
    
    _value: A | None
    
    @classmethod
    def some(cls, value: A) -> Option[A]:
        return cls(value)
    
    @classmethod
    def none(cls) -> Option[A]:
        return cls(None)
    
    @classmethod
    def pure(cls, value: A) -> Option[A]:
        return cls.some(value)
    
    def map(self, f: Callable[[A], B]) -> Option[B]:
        if self._value is None:
            return Option.none()
        return Option.some(f(self._value))
    
    def ap(self: "Option[Callable[[A], B]]", fa: Option[A]) -> Option[B]:
        """Apply function from this Option to the value in fa (function.ap(value))."""
        if self._value is None or fa._value is None:
            return Option.none()
        # Self-type annotation ensures self._value is Callable[[A], B]
        return Option.some(self._value(fa._value))
    
    def bind(self, f: Callable[[A], Option[B]]) -> Option[B]:
        if self._value is None:
            return Option.none()
        return f(self._value)
    
    def get_or_else(self, default: A) -> A:
        if self._value is None:
            return default
        return self._value
    
    def is_some(self) -> bool:
        return self._value is not None
    
    def is_none(self) -> bool:
        return self._value is None
    
    def __repr__(self) -> str:
        if self._value is None:
            return "Option.none()"
        return f"Option.some({self._value})"
