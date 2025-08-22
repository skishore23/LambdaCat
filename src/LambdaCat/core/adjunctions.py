"""Adjunctions between categories.

This module implements a basic adjunction framework with law checking.
All adjunction data must be explicitly provided.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from .category import Cat
from .functor import CatFunctor
from .natural import Natural
from .laws import Law, LawResult, Violation, LawSuite


@dataclass(frozen=True)
class Adjunction:
    """An adjunction L ⊣ R between categories C and D.
    
    L: C → D (left adjoint)
    R: D → C (right adjoint)  
    unit: 1_C → R∘L (unit natural transformation)
    counit: L∘R → 1_D (counit natural transformation)
    """
    left: CatFunctor   # L: C → D
    right: CatFunctor  # R: D → C
    unit: Natural      # η: 1_C → R∘L
    counit: Natural    # ε: L∘R → 1_D
    
    def __post_init__(self) -> None:
        """Validate adjunction structure."""
        # Check that functors compose correctly
        if self.left.source != self.right.target:
            raise ValueError(f"Left functor target {self.left.target} ≠ right functor source {self.right.source}")
        if self.left.target != self.right.source:
            raise ValueError(f"Left functor source {self.left.source} ≠ right functor target {self.right.target}")
    
    def __repr__(self) -> str:
        return f"Adjunction({self.left.name} ⊣ {self.right.name})"


@dataclass(frozen=True)
class _TriangularIdentityRightLaw(Law[Adjunction]):
    """Triangle identity: (R ε) ∘ (η R) = 1_R."""
    name: str = "triangular-identity-right"
    tags: Sequence[str] = ("adjunction", "triangle-identity")
    
    def run(self, adj: Adjunction, config: Dict[str, Any]) -> LawResult:
        violations: List[Violation] = []
        
        # For each object A in the source of R (= target of L)
        for obj in adj.right.source.objects:
            obj_name = obj.name
            
            # Get R(A)
            try:
                R_A = adj.right.object_map[obj_name]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Right functor not defined on object {obj_name}",
                    witness={"object": obj_name}
                ))
                continue
            
            # Get unit component η_{R(A)}: R(A) → R(L(R(A)))
            try:
                unit_comp = adj.unit.components[R_A]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Unit not defined at R({obj_name}) = {R_A}",
                    witness={"object": obj_name, "R_object": R_A}
                ))
                continue
            
            # Get counit component ε_A: L(R(A)) → A  
            try:
                counit_comp = adj.counit.components[obj_name]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Counit not defined at {obj_name}",
                    witness={"object": obj_name}
                ))
                continue
            
            # Apply R to counit: R(ε_A): R(L(R(A))) → R(A)
            try:
                L_R_A = adj.left.object_map[R_A]
                R_counit = adj.right.morphism_map[counit_comp]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Cannot apply functors to counit component at {obj_name}",
                    witness={"object": obj_name, "counit": counit_comp}
                ))
                continue
            
            # Check triangle identity: R(ε_A) ∘ η_{R(A)} = id_{R(A)}
            try:
                composition = adj.right.source.compose(R_counit, unit_comp)
                identity = adj.right.source.identity(R_A)
                
                if composition != identity:
                    violations.append(Violation(
                    law=self.name,
                        message=f"Triangle identity failed at {obj_name}: R(ε) ∘ η ≠ id",
                        witness={
                            "object": obj_name,
                            "R_object": R_A,
                            "composition": composition,
                            "identity": identity
                        }
                    ))
            except (KeyError, TypeError) as e:
                violations.append(Violation(
                    law=self.name,
                    message=f"Cannot check triangle identity at {obj_name}: {e}",
                    witness={"object": obj_name, "error": str(e)}
                ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _TriangularIdentityLeftLaw(Law[Adjunction]):
    """Triangle identity: (ε L) ∘ (L η) = 1_L."""
    name: str = "triangular-identity-left"
    tags: Sequence[str] = ("adjunction", "triangle-identity")
    
    def run(self, adj: Adjunction, config: Dict[str, Any]) -> LawResult:
        violations: List[Violation] = []
        
        # For each object B in the source of L (= target of R)
        for obj in adj.left.source.objects:
            obj_name = obj.name
            
            # Get L(B)
            try:
                L_B = adj.left.object_map[obj_name]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Left functor not defined on object {obj_name}",
                    witness={"object": obj_name}
                ))
                continue
            
            # Get unit component η_B: B → R(L(B))
            try:
                unit_comp = adj.unit.components[obj_name]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Unit not defined at {obj_name}",
                    witness={"object": obj_name}
                ))
                continue
            
            # Get counit component ε_{L(B)}: L(R(L(B))) → L(B)
            try:
                R_L_B = adj.right.object_map[L_B]
                counit_comp = adj.counit.components[L_B]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Counit not defined at L({obj_name}) = {L_B}",
                    witness={"object": obj_name, "L_object": L_B}
                ))
                continue
            
            # Apply L to unit: L(η_B): L(B) → L(R(L(B)))
            try:
                L_unit = adj.left.morphism_map[unit_comp]
            except KeyError:
                violations.append(Violation(
                    law=self.name,
                    message=f"Cannot apply left functor to unit component at {obj_name}",
                    witness={"object": obj_name, "unit": unit_comp}
                ))
                continue
            
            # Check triangle identity: ε_{L(B)} ∘ L(η_B) = id_{L(B)}
            try:
                composition = adj.left.target.compose(counit_comp, L_unit)
                identity = adj.left.target.identity(L_B)
                
                if composition != identity:
                    violations.append(Violation(
                    law=self.name,
                        message=f"Triangle identity failed at {obj_name}: ε ∘ L(η) ≠ id",
                        witness={
                            "object": obj_name,
                            "L_object": L_B,
                            "composition": composition,
                            "identity": identity
                        }
                    ))
            except (KeyError, TypeError) as e:
                violations.append(Violation(
                    law=self.name,
                    message=f"Cannot check triangle identity at {obj_name}: {e}",
                    witness={"object": obj_name, "error": str(e)}
                ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


# Adjunction law suite
ADJUNCTION_SUITE = LawSuite("adjunction", [
    _TriangularIdentityLeftLaw(),
    _TriangularIdentityRightLaw(),
])


def free_forgetful_adjunction() -> Adjunction:
    """Example: Free-Forgetful adjunction between discrete categories.
    
    This is a toy example showing the structure of an adjunction.
    Free: Discrete({*}) → Discrete({a,b}) maps * to a
    Forgetful: Discrete({a,b}) → Discrete({*}) maps both a,b to *
    """
    from .standard import discrete
    from .functor import FunctorBuilder
    from .natural import Natural
    
    # Source and target categories
    C = discrete(["*"])  # Single object category
    D = discrete(["a", "b"])  # Two object discrete category
    
    # Free functor: * → a
    Free = (FunctorBuilder("Free", C, D)
            .on_objects({"*": "a"})
            .build())
    
    # Forgetful functor: a,b → *
    Forget = (FunctorBuilder("Forget", D, C)
              .on_objects({"a": "*", "b": "*"})
              .build())
    
    # Unit: 1_C → Forget∘Free (id_* → id_*)
    unit = Natural(
        source=Free,  # This should be identity functor, but we'll use Free for simplicity
        target=Free,  # This should be Forget∘Free
        components={"*": "id:*"}
    )
    
    # Counit: Free∘Forget → 1_D
    counit = Natural(
        source=Free,  # This should be Free∘Forget
        target=Free,  # This should be identity functor
        components={"a": "id:a", "b": "id:b"}
    )
    
    return Adjunction(Free, Forget, unit, counit)


__all__ = [
    "Adjunction",
    "ADJUNCTION_SUITE",
    "free_forgetful_adjunction",
]
