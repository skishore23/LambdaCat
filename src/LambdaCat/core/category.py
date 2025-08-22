from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, TypedDict, List

from .presentation import Obj, ArrowGen, Formal1, Presentation


class ArrowDict(TypedDict):
	name: str
	source: str
	target: str


class CategoryJSON(TypedDict):
	objects: List[str]
	arrows: List[ArrowDict]
	composition: Dict[str, str]
	identities: Dict[str, str]


@dataclass(frozen=True)
class Cat:
	objects: Tuple[Obj, ...]
	arrows: Tuple[ArrowGen, ...]
	composition: Dict[Tuple[str, str], str]
	identities: Dict[str, str]

	def __repr__(self) -> str:  # pragma: no cover
		return f"Cat(|Obj|={len(self.objects)}, |Arr|={len(self.arrows)})"

	@staticmethod
	def from_presentation(p: Presentation) -> "Cat":
		ids = {o.name: f"id:{o.name}" for o in p.objects}
		# Seed composition with identity laws for all arrows present in presentation
		comp: Dict[Tuple[str, str], str] = {}
		by_obj_id: Dict[str, str] = ids
		for a in p.arrows:
			id_src = by_obj_id.get(a.source)
			id_tgt = by_obj_id.get(a.target)
			if id_src is not None:
				comp[(a.name, id_src)] = a.name  # f ∘ id_src = f
			if id_tgt is not None:
				comp[(id_tgt, a.name)] = a.name  # id_tgt ∘ f = f
		return Cat(p.objects, p.arrows, comp, ids)

	def compose(self, left: str, right: str) -> str:
		try:
			left_arrow = next(a for a in self.arrows if a.name == left)
			right_arrow = next(a for a in self.arrows if a.name == right)
		except StopIteration as e:
			raise KeyError(f"unknown arrow name in compose: ({left},{right})") from e
		# Typed guard: dom(left) must equal cod(right) for (left∘right)
		if left_arrow.source != right_arrow.target:
			raise TypeError(
				f"ill-typed compose: dom({left})={left_arrow.source} ≠ cod({right})={right_arrow.target}"
			)
		key = (left, right)
		if key not in self.composition:
			raise KeyError(f"composition not defined for typed pair ({left},{right})")
		return self.composition[key]

	def identity(self, obj_name: str) -> str:
		try:
			return self.identities[obj_name]
		except KeyError as e:
			raise KeyError(f"no identity for object {obj_name}") from e

	def op(self) -> "Cat":
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
	def from_json(cls, data: CategoryJSON) -> "Cat":
		"""Create category from JSON data."""
		from .presentation import Obj, ArrowGen
		
		objects = tuple(Obj(name) for name in data["objects"])
		arrows = tuple(ArrowGen(arr["name"], arr["source"], arr["target"]) for arr in data["arrows"])
		
		# Parse composition table
		composition = {}
		for key, value in data["composition"].items():
			f, g = key.split(",", 1)
			composition[(f, g)] = value
		
		identities = data["identities"]
		
		return cls(objects, arrows, composition, identities)

	def slice(self, A: str) -> "Cat":
		"""Create slice category C/A."""
		from .ops_category import slice_category
		return slice_category(self, A)

