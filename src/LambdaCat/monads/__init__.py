from __future__ import annotations

# Public namespace re-exporting existing FP instances; core remains independent
from LambdaCat.core.fp.instances.identity import Id as Identity
from LambdaCat.core.fp.instances.maybe import Maybe
from LambdaCat.core.fp.instances.option import Option
from LambdaCat.core.fp.instances.result import Result
from LambdaCat.core.fp.instances.either import Either
from LambdaCat.core.fp.instances.reader import Reader
from LambdaCat.core.fp.instances.state import State
from LambdaCat.core.fp.instances.writer import Writer
from LambdaCat.core.fp.instances.list import List
from LambdaCat.core.fp.instances.nonemptylist import NonEmptyList
from LambdaCat.core.laws_monad import MONAD_SUITE
from LambdaCat.core.laws_applicative import APPLICATIVE_SUITE
from LambdaCat.core.laws_functor import FUNCTOR_SUITE

__all__ = [
    "Identity",
    "Maybe",
    "Option",
    "Result", 
    "Either",
    "Reader",
    "State",
    "Writer",
    "List",
    "NonEmptyList",
    "MONAD_SUITE",
    "APPLICATIVE_SUITE",
    "FUNCTOR_SUITE",
]


