"""FP instances for LambdaCat."""

from .either import Either
from .identity import Id
from .list import List
from .maybe import Maybe
from .nonemptylist import NonEmptyList
from .option import Option
from .reader import Reader
from .result import Result
from .semigroup import (
    FunctionSemigroup,
    IntAddSemigroup,
    IntMulSemigroup,
    ListSemigroup,
    Semigroup,
    StringSemigroup,
)
from .state import State
from .writer import Writer

__all__ = [
    "Id",
    "Maybe",
    "Option",
    "Result",
    "Either",
    "Reader",
    "Writer",
    "State",
    "List",
    "NonEmptyList",
    "Semigroup",
    "StringSemigroup",
    "ListSemigroup",
    "IntAddSemigroup",
    "IntMulSemigroup",
    "FunctionSemigroup",
]
