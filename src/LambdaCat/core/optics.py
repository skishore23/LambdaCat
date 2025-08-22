from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
D = TypeVar("D")
S = TypeVar("S")
T = TypeVar("T")


@dataclass(frozen=True)
class Lens(Generic[S, T, A, B]):
    """Lens optic for immutable state access and modification."""
    
    get: Callable[[S], A]
    set: Callable[[B, S], T]
    
    def modify(self, f: Callable[[A], B]) -> Callable[[S], T]:
        """Modify the focused value using function f."""
        return lambda s: self.set(f(self.get(s)), s)
    
    def compose(self, other: Lens[A, B, C, D]) -> Lens[S, T, C, D]:
        """Compose two lenses: self ∘ other"""
        return Lens(
            get=lambda s: other.get(self.get(s)),
            set=lambda c, s: self.set(other.set(c, self.get(s)), s)
        )
    
    def __or__(self, other: Lens[A, B, C, D]) -> Lens[S, T, C, D]:
        """Compose lenses using | operator."""
        return self.compose(other)


@dataclass(frozen=True)
class Prism(Generic[S, T, A, B]):
    """Prism optic for sum types and partial access."""
    
    preview: Callable[[S], A | None]
    review: Callable[[B], T]
    
    def modify(self, f: Callable[[A], B]) -> Callable[[S], T]:
        """Modify the focused value if it exists, otherwise return unchanged."""
        def modify_fn(s: S) -> T:
            a = self.preview(s)
            if a is None:
                return s
            return self.review(f(a))
        return modify_fn
    
    def compose(self, other: Prism[A, B, C, D]) -> Prism[S, T, C, D]:
        """Compose two prisms: self ∘ other"""
        return Prism(
            preview=lambda s: (lambda a: other.preview(a) if a is not None else None)(self.preview(s)),
            review=lambda c: self.review(other.review(c))
        )
    
    def __or__(self, other: Prism[A, B, C, D]) -> Prism[S, T, C, D]:
        """Compose prisms using | operator."""
        return self.compose(other)


@dataclass(frozen=True)
class Iso(Generic[S, T, A, B]):
    """Isomorphism optic for bidirectional transformations."""
    
    get: Callable[[S], A]
    set: Callable[[B], T]
    
    def modify(self, f: Callable[[A], B]) -> Callable[[S], T]:
        """Modify the focused value using function f."""
        return lambda s: self.set(f(self.get(s)))
    
    def compose(self, other: Iso[A, B, C, D]) -> Iso[S, T, C, D]:
        """Compose two isomorphisms: self ∘ other"""
        return Iso(
            get=lambda s: other.get(self.get(s)),
            set=lambda c: self.set(other.set(c))
        )
    
    def __or__(self, other: Iso[A, B, C, D]) -> Iso[S, T, C, D]:
        """Compose isomorphisms using | operator."""
        return self.compose(other)
    
    def reverse(self) -> Iso[B, A, T, S]:
        """Reverse the isomorphism."""
        return Iso(get=self.set, set=self.get)


# Common lens constructors
def lens(get: Callable[[S], A], set: Callable[[B, S], T]) -> Lens[S, T, A, B]:
    """Create a lens from get and set functions."""
    return Lens(get=get, set=set)


def prism(preview: Callable[[S], A | None], review: Callable[[B], T]) -> Prism[S, T, A, B]:
    """Create a prism from preview and review functions."""
    return Prism(preview=preview, review=review)


def iso(get: Callable[[S], A], set: Callable[[B], T]) -> Iso[S, T, A, B]:
    """Create an isomorphism from get and set functions."""
    return Iso(get=get, set=set)


# Utility functions
def focus(lens: Lens[S, T, A, B], f: Callable[[A], B]) -> Callable[[S], T]:
    """Focus on a value using a lens and apply a function."""
    return lens.modify(f)


def view(lens: Lens[S, T, A, B], s: S) -> A:
    """View the focused value."""
    return lens.get(s)


def set_value(lens: Lens[S, T, A, B], b: B, s: S) -> T:
    """Set the focused value."""
    return lens.set(b, s)


def preview(prism: Prism[S, T, A, B], s: S) -> A | None:
    """Preview the focused value if it exists."""
    return prism.preview(s)


def review(prism: Prism[S, T, A, B], b: B) -> T:
    """Review a value into the prism's target type."""
    return prism.review(b)
