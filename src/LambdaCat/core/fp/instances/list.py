from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


@dataclass(frozen=True)
class List(Generic[A]):
    """List monad with functional operations."""

    items: tuple[A, ...]

    @classmethod
    def empty(cls) -> List[A]:
        """Create an empty list."""
        return cls(())

    @classmethod
    def of(cls, *items: A) -> List[A]:
        """Create a list from items."""
        return cls(items)

    @classmethod
    def from_list(cls, items: list[A]) -> List[A]:
        """Create from a regular Python list."""
        return cls(tuple(items))

    @classmethod
    def pure(cls, value: A) -> List[A]:
        """Applicative pure - create singleton list."""
        return cls((value,))

    def to_list(self) -> list[A]:
        """Convert to regular Python list."""
        return list(self.items)

    def is_empty(self) -> bool:
        """Check if the list is empty."""
        return len(self.items) == 0

    def length(self) -> int:
        """Get the length of the list."""
        return len(self.items)

    def head(self) -> A:
        """Get the first element. Raises IndexError if empty."""
        if self.is_empty():
            raise IndexError("head() called on empty list")
        return self.items[0]

    def tail(self) -> List[A]:
        """Get all elements except the first. Raises IndexError if empty."""
        if self.is_empty():
            raise IndexError("tail() called on empty list")
        return List(self.items[1:])

    def map(self, f: Callable[[A], B]) -> List[B]:
        """Functor map operation."""
        return List(tuple(f(x) for x in self.items))

    def ap(self, other: List[A]) -> List[B]:
        """Applicative apply - cartesian product of functions and values."""
        results: list[B] = []

        for func in self.items:
            for value in other.items:
                results.append(func(value))  # type: ignore[operator]

        return List.from_list(results)

    def bind(self, f: Callable[[A], List[B]]) -> List[B]:
        """Monadic bind operation (flat map)."""
        results: list[B] = []

        for x in self.items:
            inner_list = f(x)
            results.extend(inner_list.items)

        return List.from_list(results)

    def concat(self, other: List[A]) -> List[A]:
        """Concatenate two lists."""
        return List(self.items + other.items)

    def reverse(self) -> List[A]:
        """Reverse the list."""
        return List(tuple(reversed(self.items)))

    def filter(self, predicate: Callable[[A], bool]) -> List[A]:
        """Filter elements."""
        return List(tuple(x for x in self.items if predicate(x)))

    def take(self, n: int) -> List[A]:
        """Take the first n elements."""
        return List(self.items[:n])

    def drop(self, n: int) -> List[A]:
        """Drop the first n elements."""
        return List(self.items[n:])

    def fold_left(self, initial: B, f: Callable[[B, A], B]) -> B:
        """Left fold with initial value."""
        result = initial
        for x in self.items:
            result = f(result, x)
        return result

    def fold_right(self, initial: B, f: Callable[[A, B], B]) -> B:
        """Right fold with initial value."""
        result = initial
        for x in reversed(self.items):
            result = f(x, result)
        return result

    def zip_with(self, other: List[B], f: Callable[[A, B], C]) -> List[C]:
        """Zip two lists with a combining function."""
        results: list[C] = []

        for a, b in zip(self.items, other.items):
            results.append(f(a, b))

        return List.from_list(results)

    def __iter__(self) -> ListIterator[A]:
        """Make iterable."""
        return ListIterator(self.items)

    def __len__(self) -> int:
        """Support len() function."""
        return self.length()

    def __getitem__(self, index: int) -> A:
        """Support indexing."""
        return self.items[index]

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, List):
            return False
        return self.items == other.items

    def __repr__(self) -> str:
        return f"List({list(self.items)})"


@dataclass(frozen=True)
class ListIterator(Generic[A]):
    items: tuple[A, ...]
    index: int = 0

    def __iter__(self) -> ListIterator[A]:
        return self

    def __next__(self) -> A:
        if self.index < len(self.items):
            value = self.items[self.index]
            self.__dict__["index"] = self.index + 1
            return value
        raise StopIteration
