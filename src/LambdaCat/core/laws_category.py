from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .category import Cat
from .laws import ConfigDict, Law, LawResult, LawSuite, Violation


def _composable(C: Cat, f: str, g: str) -> bool:
	# Compose g ∘ f means (g,f) key in the composition table
	return (g, f) in C.composition


@dataclass(frozen=True)
class _IdentitiesLaw(Law[Cat]):
	name: str = "identities"
	tags: Sequence[str] = ("category", "core")

	def run(self, C: Cat, config: ConfigDict) -> LawResult[Cat]:
		violations: list[Violation[Cat]] = []
		for _obj_name, id_name in C.identities.items():
			# right and left identity for any morphism incident to obj
			for (left, right), h in C.composition.items():
				# right identity: (f, id_src) = f
				if right == id_name and h != left:
					violations.append(Violation(self.name, "f ∘ id_src ≠ f", {"f": left}))
				# left identity: (id_tgt, f) = f
				if left == id_name and h != right:
					violations.append(Violation(self.name, "id_tgt ∘ f ≠ f", {"f": right}))
		return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _AssociativityLaw(Law[Cat]):
	name: str = "associativity"
	tags: Sequence[str] = ("category", "core")

	def run(self, C: Cat, config: ConfigDict) -> LawResult[Cat]:
		limit_val = config.get("assoc_sample_limit", 0)
		limit = int(limit_val) if isinstance(limit_val, (int, str)) else 0  # 0 = exhaustive
		count = 0
		violations: list[Violation[Cat]] = []
		pairs = list(C.composition.keys())
		# iterate composable triples via composition table keys
		for (g, f) in pairs:
			for (h, g2) in pairs:
				if g2 != g:
					continue
				if limit and count >= limit:
					break
				count += 1
				try:
					left = C.composition[(h, C.composition[(g, f)])]
					right = C.composition[(C.composition[(h, g)], f)]
					if left != right:
						violations.append(
							Violation(self.name, "(h∘g)∘f ≠ h∘(g∘f)", {"h": h, "g": g, "f": f})
						)
				except Exception as e:
					violations.append(
						Violation(self.name, f"compose error: {e}", {"h": h, "g": g, "f": f})
					)
		return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _WellTypedComposition(Law[Cat]):
	name: str = "well-typed-composition"
	tags: Sequence[str] = ("category", "core")

	def run(self, C: Cat, config: ConfigDict) -> LawResult[Cat]:
		violations: list[Violation[Cat]] = []
		# If cod(f)==dom(g), then (g,f) must appear in composition table and with correct typing
		# Build lookup for arrows by name
		by_name = {a.name: a for a in C.arrows}
		for f_name, f in by_name.items():
			for g_name, g in by_name.items():
				if f.target != g.source:
					continue
				key = (g_name, f_name)
				if key not in C.composition:
					violations.append(Violation(self.name, "missing composite for typed pair", {"g": g_name, "f": f_name}))
					continue
				h_name = C.composition[key]
				if h_name not in by_name:
					violations.append(Violation(self.name, "composite not an arrow name", {"h": h_name}))
					continue
				h = by_name[h_name]
				if not (h.source == f.source and h.target == g.target):
					violations.append(
						Violation(self.name, "typed endpoints of composite mismatch", {"g": g_name, "f": f_name, "h": h_name})
					)
		return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


CATEGORY_SUITE = LawSuite[Cat]("category-core", laws=[_IdentitiesLaw(), _AssociativityLaw(), _WellTypedComposition()])


