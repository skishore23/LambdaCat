from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class NonEmptyList(Generic[A]):
    """Non-empty list with guaranteed at least one element."""

    head: A
    tail: tuple[A, ...]

    @classmethod
    def of(cls, head: A, *tail: A) -> NonEmptyList[A]:
        """Create a non-empty list from head and tail elements."""
        return cls(head, tail)

    @classmethod
    def single(cls, value: A) -> NonEmptyList[A]:
        """Create a non-empty list with a single element."""
        return cls(value, ())

    @classmethod
    def from_list(cls, items: list[A]) -> NonEmptyList[A]:
        """Create from a regular list. Raises ValueError if empty."""
        if not items:
            raise ValueError("Cannot create NonEmptyList from empty list")
        return cls(items[0], tuple(items[1:]))

    @classmethod
    def pure(cls, value: A) -> NonEmptyList[A]:
        """Applicative pure - create singleton list."""
        return cls.single(value)

    def to_list(self) -> list[A]:
        """Convert to regular list."""
        return [self.head] + list(self.tail)

    def length(self) -> int:
        """Get the length of the list."""
        return 1 + len(self.tail)

    def map(self, f: Callable[[A], B]) -> NonEmptyList[B]:
        """Functor map operation."""
        return NonEmptyList(f(self.head), tuple(f(x) for x in self.tail))

    def ap(self, other: NonEmptyList[A]) -> NonEmptyList[B]:
        """Applicative apply - cartesian product of functions and values."""
        results: list[B] = []

        # Apply head function to all values
        for value in other.to_list():
            results.append(self.head(value))  # type: ignore[operator]

        # Apply tail functions to all values
        for func in self.tail:
            for value in other.to_list():
                results.append(func(value))  # type: ignore[operator]

        return NonEmptyList.from_list(results)

    def bind(self, f: Callable[[A], NonEmptyList[B]]) -> NonEmptyList[B]:
        """Monadic bind operation."""
        result = f(self.head)

        for x in self.tail:
            next_result = f(x)
            result = result.concat(next_result)

        return result

    def concat(self, other: NonEmptyList[A]) -> NonEmptyList[A]:
        """Concatenate two non-empty lists."""
        return NonEmptyList(self.head, self.tail + (other.head,) + other.tail)

    def reverse(self) -> NonEmptyList[A]:
        """Reverse the list."""
        items = self.to_list()
        items.reverse()
        return NonEmptyList.from_list(items)

    def filter(self, predicate: Callable[[A], bool]) -> list[A]:
        """Filter elements (may result in empty list)."""
        return [x for x in self.to_list() if predicate(x)]

    def fold(self, f: Callable[[A, A], A]) -> A:
        """Fold the list using the semigroup operation."""
        result = self.head
        for x in self.tail:
            result = f(result, x)
        return result

    def __iter__(self) -> NonEmptyListIterator[A]:
        """Make iterable."""
        return NonEmptyListIterator(self.head, self.tail)

    def __len__(self) -> int:
        """Support len() function."""
        return self.length()

    def __getitem__(self, index: int) -> A:
        """Support indexing."""
        if index == 0:
            return self.head
        elif 1 <= index <= len(self.tail):
            return self.tail[index - 1]
        else:
            raise IndexError(f"Index {index} out of range for NonEmptyList of length {self.length()}")

    def __repr__(self) -> str:
        return f"NonEmptyList({self.head}, {self.tail})"


# Semigroup instance for NonEmptyList
@dataclass(frozen=True)
class NonEmptyListSemigroup(Generic[A]):
    """Semigroup instance for NonEmptyList - concatenation."""

    def combine(self, left: NonEmptyList[A], right: NonEmptyList[A]) -> NonEmptyList[A]:
        return left.concat(right)


@dataclass(frozen=True)
class NonEmptyListIterator(Generic[A]):
    head: A
    tail: tuple[A, ...]
    index: int = 0

    def __iter__(self) -> NonEmptyListIterator[A]:
        return self

    def __next__(self) -> A:
        if self.index == 0:
            self.__dict__["index"] = 1
            return self.head
        i = self.index - 1
        if i < len(self.tail):
            self.__dict__["index"] = self.index + 1
            return self.tail[i]
        raise StopIteration
