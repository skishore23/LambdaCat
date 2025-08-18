from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Mapping, Tuple, TypeVar

from .typeclasses import MonadT
from ..presentation import Obj, ArrowGen
from ..category import Cat


A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


@dataclass(frozen=True)
class Kleisli(Generic[A, B]):
	"""Kleisli arrow for a monad.

	Wraps a function `run: A -> M[B]` and composes via monadic bind.
	Pure helper is provided by `kleisli_identity` which requires a `pure` function.
	"""

	run: Callable[[A], MonadT[B]]

	def then(self, g: "Kleisli[B, C]") -> "Kleisli[A, C]":
		return Kleisli(lambda a: self.run(a).bind(g.run))


def kleisli_identity(pure: Callable[[A], MonadT[A]]) -> Kleisli[A, A]:
	"""Identity arrow for a given monad, provided as a `pure` function.

	Example: `kleisli_identity(Maybe.pure)` or `kleisli_identity(Id.pure)`.
	"""

	return Kleisli(lambda a: pure(a))


def kleisli_category(
	name: str,
	objects: Tuple[str, ...],
	morphisms: Mapping[str, Tuple[str, str]],
	compose_semantics: Mapping[Tuple[str, str], str],
) -> Cat:
	"""Build a small `Cat` representing the shape of a Kleisli graph.

	This is a structural category over names only; it does not embed monad code.
	Use when you want to run `CATEGORY_SUITE` on the arrow shape you define.
	"""

	objs = tuple(Obj(o) for o in objects)
	arrows = tuple(ArrowGen(k, src, tgt) for k, (src, tgt) in morphisms.items())
	identities = {o: f"id:{o}" for o in objects}
	C = Cat(objects=objs, arrows=arrows, composition=dict(compose_semantics), identities=identities)
	return C


