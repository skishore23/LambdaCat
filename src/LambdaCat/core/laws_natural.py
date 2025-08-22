from __future__ import annotations

from .laws import Law, LawResult, LawSuite, Violation
from .natural import Natural


class _NaturalityWellTyped(Law[Natural]):
    name = "naturality-components-typed"
    tags = ("natural", "core")

    def run(self, eta: Natural, config):
        V: list[Violation] = []
        F, G = eta.source, eta.target
        if not (F.source is G.source and F.target is G.target):
            V.append(Violation(self.name, "Functors must have same source/target", {}))
            return LawResult(self.name, passed=False, violations=V)
        S = F.source
        T = F.target
        # Components must exist and have correct typing FX -> GX
        for X in S.objects:
            Xn = X.name
            if Xn not in eta.components:
                V.append(Violation(self.name, f"Missing η_{Xn}", {"X": Xn}))
                continue
            eta_X = eta.components[Xn]
            # Find arrow in target
            try:
                aX = next(a for a in T.arrows if a.name == eta_X)
            except StopIteration:
                V.append(Violation(self.name, f"Missing component arrow in target for η_{Xn}", {"X": Xn}))
                continue
            FX = F.object_map.get(Xn)
            GX = G.object_map.get(Xn)
            if FX is None or GX is None:
                V.append(Violation(self.name, f"Missing object map for {Xn}", {"X": Xn}))
                continue
            if not (aX.source == FX and aX.target == GX):
                V.append(
                    Violation(
                        self.name,
                        f"η_{Xn} has wrong type: expected {FX}->{GX}, got {aX.source}->{aX.target}",
                        {"X": Xn},
                    )
                )
        return LawResult(self.name, passed=(len(V) == 0), violations=V)


class _NaturalitySquares(Law[Natural]):
    name = "naturality-squares"
    tags = ("natural", "core")

    def run(self, eta: Natural, config):
        V: list[Violation] = []
        F, G = eta.source, eta.target
        S = F.source
        T = F.target
        for a in S.arrows:
            f = a.name
            X = a.source
            Y = a.target
            if X not in eta.components or Y not in eta.components:
                V.append(Violation(self.name, f"Missing components for {X} or {Y}", {"f": f}))
                continue
            eta_X = eta.components[X]
            eta_Y = eta.components[Y]
            Ff = F.morphism_map.get(f)
            Gf = G.morphism_map.get(f)
            if Ff is None or Gf is None:
                V.append(Violation(self.name, f"Functor not defined on morphism {f}", {"f": f}))
                continue
            try:
                left = T.compose(eta_Y, Ff)
                right = T.compose(Gf, eta_X)
            except KeyError as e:
                V.append(Violation(self.name, f"Composition missing: {e}", {"f": f}))
                continue
            if left != right:
                V.append(Violation(self.name, f"Naturality failed on {f}", {"f": f}))
        return LawResult(self.name, passed=(len(V) == 0), violations=V)


NATURAL_SUITE = LawSuite[Natural]("natural-core", laws=[_NaturalityWellTyped(), _NaturalitySquares()])


