from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ..typeclasses import Monoid

A = TypeVar("A")
B = TypeVar("B")
W = TypeVar("W")


@dataclass(frozen=True)
class Writer(Generic[W, A]):
    """Writer monad for accumulating logs."""

    value: A
    log: W
    _monoid: Monoid[W]

    @classmethod
    def pure(cls, value: A, monoid: Monoid[W] | None = None) -> Writer[W, A]:
        """Construct a Writer with empty log.

        Accepts an optional monoid to avoid relying on class state; if omitted,
        requires a previously set class-level monoid via set_monoid.
        """
        m = monoid if monoid is not None else getattr(cls, '_default_monoid', None)
        if m is None:
            raise TypeError("Writer.pure requires monoid instance for log type")
        return cls(value, m.empty(), m)

    def map(self, f: Callable[[A], B]) -> Writer[W, B]:
        return Writer(f(self.value), self.log, self._monoid)

    def ap(self: Writer[W, Callable[[A], B]], wa: Writer[W, A]) -> Writer[W, B]:
        """Apply function from this Writer to the value in wa (function.ap(value))."""
        m = self._monoid
        return Writer(self.value(wa.value), m.combine(self.log, wa.log), m)

    def bind(self, f: Callable[[A], Writer[W, B]]) -> Writer[W, B]:
        m = self._monoid
        result = f(self.value)
        return Writer(result.value, m.combine(self.log, result.log), m)

    def tell(self, message: W) -> Writer[W, A]:
        m = self._monoid
        return Writer(self.value, m.combine(self.log, message), m)

    def listen(self) -> Writer[W, tuple[A, W]]:
        return Writer((self.value, self.log), self.log, self._monoid)

    def pass_(self, f: Callable[[W], W]) -> Writer[W, A]:
        return Writer(self.value, f(self.log), self._monoid)

    @classmethod
    def set_monoid(cls, monoid: Monoid[W]) -> None:
        cls._default_monoid = monoid

    # Optional default monoid for pure() when not provided explicitly
    _default_monoid: Monoid[W] | None = None

    def __repr__(self) -> str:
        return f"Writer({self.value}, {self.log})"


# Convenience constructor to preserve demo ergonomics
def writer(value: A, log: W, monoid: Monoid[W] | None = None) -> Writer[W, A]:
    m = monoid if monoid is not None else getattr(Writer, '_default_monoid', None)
    if m is None:
        raise TypeError("writer() requires a monoid instance or a default set via Writer.set_monoid")
    return Writer(value, log, m)


