from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .category import Cat
from .functor import CatFunctor


@dataclass(frozen=True)
class Natural:
	source: CatFunctor  # F
	target: CatFunctor  # G
	components: Mapping[str, str]  # key: object name X, value: morph name η_X in target cat

	def __repr__(self) -> str:
		comp_count = len(self.components)
		return f"Natural({self.source.name} → {self.target.name}, {comp_count} components)"


def check_naturality(eta: Natural) -> None:
	F, G = eta.source, eta.target
	if not (F.source is G.source and F.target is G.target):
		raise AssertionError("Functors must have same source/target for naturality")
	S: Cat = F.source
	T: Cat = F.target
	for a in S.arrows:
		f = a.name
		X = a.source
		Y = a.target
		if X not in eta.components:
			raise AssertionError(f"Missing natural component for object {X}")
		if Y not in eta.components:
			raise AssertionError(f"Missing natural component for object {Y}")
		eta_X = eta.components[X]
		eta_Y = eta.components[Y]
		Ff = F.morphism_map.get(f)
		Gf = G.morphism_map.get(f)
		if Ff is None or Gf is None:
			raise AssertionError(f"Functor not defined on morphism {f}")
		# Validate component arrows exist and have correct typing in target
		try:
			eta_X_arrow = next(ax for ax in T.arrows if ax.name == eta_X)
			eta_Y_arrow = next(ay for ay in T.arrows if ay.name == eta_Y)
		except StopIteration:
			raise AssertionError(f"Missing component arrow in target for η_{X} or η_{Y}")
		FX = F.object_map.get(X)
		GX = G.object_map.get(X)
		FY = F.object_map.get(Y)
		GY = G.object_map.get(Y)
		if FX is None or GX is None or FY is None or GY is None:
			raise AssertionError("Functor object maps incomplete for naturality check")
		if not (eta_X_arrow.source == FX and eta_X_arrow.target == GX):
			raise AssertionError(
				f"η_{X} has wrong type: expected {FX}->{GX}, got {eta_X_arrow.source}->{eta_X_arrow.target}"
			)
		if not (eta_Y_arrow.source == FY and eta_Y_arrow.target == GY):
			raise AssertionError(
				f"η_{Y} has wrong type: expected {FY}->{GY}, got {eta_Y_arrow.source}->{eta_Y_arrow.target}"
			)
		# Check η_Y ∘ F(f) == G(f) ∘ η_X in target category
		try:
			left = T.compose(eta_Y, Ff)
			right = T.compose(Gf, eta_X)
		except KeyError as e:
			raise AssertionError(f"Composition missing while checking naturality for {f}: {e}")
		if left != right:
			raise AssertionError(f"Naturality failed on {f}: η_Y ∘ F(f) != G(f) ∘ η_X")

