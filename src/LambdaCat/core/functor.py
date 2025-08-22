from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable

from .category import Cat
from .presentation import Formal1


@dataclass(frozen=True)
class Functor:
	name: str
	object_map: dict[str, str]
	morphism_map: dict[str, str]

	def __repr__(self) -> str:
		obj_count = len(self.object_map)
		mor_count = len(self.morphism_map)
		return f"Functor({self.name}: {obj_count} objects, {mor_count} morphisms)"


def apply_functor(F: Functor, path: Formal1) -> Formal1:
	factors = tuple(F.morphism_map[f] for f in path.factors)
	return Formal1(factors)


@dataclass(frozen=True)
class CatFunctor:
	name: str
	source: Cat
	target: Cat
	object_map: Mapping[str, str]
	morphism_map: Mapping[str, str]

	# FunctorT instance (map on morphism names as values)
	def map(self, f: Callable[[object], object]) -> CatFunctor:
		# No-op map since CatFunctor is not a value container; provided for law harness compatibility
		return self

	def __repr__(self) -> str:
		src_name = self.source.__class__.__name__
		tgt_name = self.target.__class__.__name__
		obj_count = len(self.object_map)
		mor_count = len(self.morphism_map)
		return f"CatFunctor({self.name}: {src_name} → {tgt_name}, {obj_count} objects, {mor_count} morphisms)"


class FunctorBuilder:
	def __init__(self, name: str, source: Cat, target: Cat):
		self.name = name
		self.source = source
		self.target = target
		self._obj: dict[str, str] = {}
		self._mor: dict[str, str] = {}

	def on_objects(self, mapping: dict[str, str]) -> FunctorBuilder:
		for s_name, t_name in mapping.items():
			self._obj[s_name] = t_name
		return self

	def on_morphisms(self, mapping: dict[str, str]) -> FunctorBuilder:
		for s_name, t_name in mapping.items():
			self._mor[s_name] = t_name
		return self

	def build(self) -> CatFunctor:
		# identities: ensure mapped
		for obj_name, id_src in self.source.identities.items():
			FX = self._obj.get(obj_name)
			if FX is None:
				raise AssertionError(f"missing object map for {obj_name}")
			id_tgt = self.target.identities.get(FX)
			if id_tgt is None:
				raise AssertionError(f"missing identity in target for {FX}")
			self._mor[id_src] = id_tgt

		# composition closure: add images of known composites
		changed = True
		while changed:
			changed = False
			for (g, f), gf in self.source.composition.items():
				if g in self._mor and f in self._mor and gf not in self._mor:
					self._mor[gf] = self.target.compose(self._mor[g], self._mor[f])
					changed = True

		F = CatFunctor(self.name, self.source, self.target, dict(self._obj), dict(self._mor))

		# Law checks: identities and composition preservation
		for obj_name, id_src in self.source.identities.items():
			FX = F.object_map[obj_name]
			id_tgt = self.target.identities[FX]
			if F.morphism_map[id_src] != id_tgt:
				raise AssertionError(f"F(id_{obj_name}) ≠ id_{FX}")
		for (g, f), gf in self.source.composition.items():
			lhs = F.morphism_map.get(gf)
			if lhs is None:
				raise AssertionError(f"F not defined on composite {gf}")
			rhs = self.target.compose(F.morphism_map[g], F.morphism_map[f])
			if lhs != rhs:
				raise AssertionError(f"F(g∘f) ≠ F(g)∘F(f) for g={g}, f={f}")

		return F

