from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Obj:
	name: str
	data: Optional[object] = None


@dataclass(frozen=True)
class ArrowGen:
	name: str
	source: str
	target: str


@dataclass(frozen=True)
class Formal1:
	# h∘...∘g∘f (rightmost applied first)
	factors: tuple[str, ...]

	def equal(self, other: 'Formal1', presentation: 'Presentation') -> bool:
		"""Check if two formal expressions are equal according to the presentation's relations.

		Uses rewriting to normalize both expressions and compare normal forms.
		"""
		from .rewriting import equal_modulo_relations
		return equal_modulo_relations(self, other, presentation)


@dataclass(frozen=True)
class Presentation:
	"""Category presentation by generators and relations.

	Note: The 'relations' field is currently informational only and not enforced
	during category construction. Future versions will support oriented rewriting
	and normal forms computation.
	"""
	objects: tuple[Obj, ...]
	arrows: tuple[ArrowGen, ...]
	relations: tuple[tuple[Formal1, Formal1], ...] = ()

	def assert_relation(self, lhs: Formal1, rhs: Formal1) -> None:
		"""Assert that a relation holds in this presentation.

		Currently only checks if the relation is declared in the presentation.
		Future versions will check if it's derivable from the declared relations.
		"""
		if (lhs, rhs) not in self.relations and (rhs, lhs) not in self.relations:
			raise AssertionError(f"Relation {lhs} = {rhs} not found in presentation")

