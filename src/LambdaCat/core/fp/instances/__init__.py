"""FP instances for LambdaCat."""

from .identity import Id
from .maybe import Maybe
from .option import Option
from .result import Result
from .either import Either
from .reader import Reader
from .writer import Writer
from .state import State
from .list import List
from .nonemptylist import NonEmptyList
from .semigroup import (
    Semigroup,
    StringSemigroup,
    ListSemigroup,
    IntAddSemigroup,
    IntMulSemigroup,
    FunctionSemigroup,
)

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
