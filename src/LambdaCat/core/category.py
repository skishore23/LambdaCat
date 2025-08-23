from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from .presentation import ArrowGen, Obj, Presentation


class ArrowDict(TypedDict):
	name: str
	source: str
	target: str


class CategoryJSON(TypedDict):
	objects: list[str]
	arrows: list[ArrowDict]
	composition: dict[str, str]
	identities: dict[str, str]


@dataclass(frozen=True)
class Cat:
	objects: tuple[Obj, ...]
	arrows: tuple[ArrowGen, ...]
	composition: dict[tuple[str, str], str]
	identities: dict[str, str]

	def __repr__(self) -> str:  # pragma: no cover
		return f"Cat(|Obj|={len(self.objects)}, |Arr|={len(self.arrows)})"

	@staticmethod
	def from_presentation(p: Presentation) -> Cat:
		ids = {o.name: f"id:{o.name}" for o in p.objects}
		# Seed composition with identity laws for all arrows present in presentation
		comp: dict[tuple[str, str], str] = {}
		by_obj_id: dict[str, str] = ids
		for a in p.arrows:
			id_src = by_obj_id.get(a.source)
			id_tgt = by_obj_id.get(a.target)
			if id_src is not None:
				comp[(a.name, id_src)] = a.name  # f ∘ id_src = f
			if id_tgt is not None:
				comp[(id_tgt, a.name)] = a.name  # id_tgt ∘ f = f
		return Cat(p.objects, p.arrows, comp, ids)

	def compose(self, left: str, right: str) -> str:
		left_arrow = None
		right_arrow = None

		# Find arrows and provide detailed error messages
		for a in self.arrows:
			if a.name == left:
				left_arrow = a
			if a.name == right:
				right_arrow = a

		if left_arrow is None:
			raise KeyError(f"Arrow '{left}' not found in category")
		if right_arrow is None:
			raise KeyError(f"Arrow '{right}' not found in category")

		# Typed guard: dom(left) must equal cod(right) for (left∘right)
		if left_arrow.source != right_arrow.target:
			raise TypeError(
				f"Cannot compose '{left}' ({left_arrow.source}→{left_arrow.target}) "
				f"with '{right}' ({right_arrow.source}→{right_arrow.target}): "
				f"domain of '{left}' ({left_arrow.source}) does not match "
				f"codomain of '{right}' ({right_arrow.target})"
			)

		key = (left, right)
		if key not in self.composition:
			raise KeyError(
				f"Composition of '{left}' ({left_arrow.source}→{left_arrow.target}) "
				f"and '{right}' ({right_arrow.source}→{right_arrow.target}) "
				f"is not defined in the composition table"
			)
		return self.composition[key]

	def identity(self, obj_name: str) -> str:
		try:
			return self.identities[obj_name]
		except KeyError as e:
			raise KeyError(f"no identity for object {obj_name}") from e

	def op(self) -> Cat:
		# Deferred import to avoid cycles
		from .ops_category import opposite_category
		return opposite_category(self)

	def to_json(self) -> CategoryJSON:
		"""Convert category to JSON-serializable format."""
		return CategoryJSON(
			objects=[obj.name for obj in self.objects],
			arrows=[ArrowDict(name=arr.name, source=arr.source, target=arr.target) for arr in self.arrows],
			composition={f"{f},{g}": h for (f, g), h in self.composition.items()},
			identities=self.identities
		)

	@classmethod
	def from_json(cls, data: CategoryJSON) -> Cat:
		"""Create category from JSON data."""
		from .presentation import ArrowGen, Obj

		objects = tuple(Obj(name) for name in data["objects"])
		arrows = tuple(ArrowGen(arr["name"], arr["source"], arr["target"]) for arr in data["arrows"])

		# Parse composition table
		composition = {}
		for key, value in data["composition"].items():
			f, g = key.split(",", 1)
			composition[(f, g)] = value

		identities = data["identities"]

		return cls(objects, arrows, composition, identities)

	def slice(self, A: str) -> Cat:
		"""Create slice category C/A."""
		from .ops_category import slice_category
		return slice_category(self, A)

