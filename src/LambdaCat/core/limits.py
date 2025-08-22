"""Limits and colimits in finite categories.

This module implements basic limits (products, equalizers) for small finite categories.
Following the fail-fast principle, operations fail explicitly when limits don't exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
from .category import Cat
from .presentation import Obj, ArrowGen


@dataclass(frozen=True)
class Cone:
    """A cone over a diagram with apex and projections."""
    apex: str
    projections: Dict[str, str]  # object -> morphism from apex
    
    def __repr__(self) -> str:
        projs = ", ".join(f"{obj}:{arr}" for obj, arr in self.projections.items())
        return f"Cone({self.apex} → {{{projs}}})"


@dataclass(frozen=True)
class Limit:
    """A limit cone that is universal."""
    cone: Cone
    
    def __repr__(self) -> str:
        return f"Limit({self.cone})"


def product(C: Cat, obj1: str, obj2: str) -> Optional[Limit]:
    """Find the product of two objects in category C.
    
    Returns None if the product doesn't exist.
    Fails fast with clear error messages for malformed inputs.
    """
    # Validate inputs
    obj_names = {obj.name for obj in C.objects}
    if obj1 not in obj_names:
        raise ValueError(f"Object {obj1} not in category")
    if obj2 not in obj_names:
        raise ValueError(f"Object {obj2} not in category")
    
    if obj1 == obj2:
        # Product of object with itself is the object (with diagonal)
        return Limit(Cone(obj1, {obj1: C.identity(obj1)}))
    
    # Look for potential product objects
    candidates: List[Tuple[str, str, str]] = []  # (product_obj, proj1, proj2)
    
    for prod_obj in obj_names:
        # Find morphisms from prod_obj to obj1 and obj2
        proj1_candidates = []
        proj2_candidates = []
        
        for arrow in C.arrows:
            if arrow.source == prod_obj and arrow.target == obj1:
                proj1_candidates.append(arrow.name)
            elif arrow.source == prod_obj and arrow.target == obj2:
                proj2_candidates.append(arrow.name)
        
        # Try all combinations of projections
        for proj1 in proj1_candidates:
            for proj2 in proj2_candidates:
                candidates.append((prod_obj, proj1, proj2))
    
    # Check universality: for each candidate, verify it's terminal among cones
    for prod_obj, proj1, proj2 in candidates:
        cone = Cone(prod_obj, {obj1: proj1, obj2: proj2})
        
        # Check if this cone is universal (terminal)
        is_universal = True
        
        # For every other cone, there must be a unique morphism to this cone
        for other_apex in obj_names:
            if other_apex == prod_obj:
                continue
                
            # Find projections from other_apex
            other_proj1 = None
            other_proj2 = None
            
            for arrow in C.arrows:
                if arrow.source == other_apex and arrow.target == obj1:
                    if other_proj1 is None:
                        other_proj1 = arrow.name
                    else:
                        # Multiple projections - not a valid cone
                        other_proj1 = None
                        break
                elif arrow.source == other_apex and arrow.target == obj2:
                    if other_proj2 is None:
                        other_proj2 = arrow.name
                    else:
                        # Multiple projections - not a valid cone
                        other_proj2 = None
                        break
            
            if other_proj1 is not None and other_proj2 is not None:
                # Found another cone, check if there's a unique factorization
                factorization = None
                
                for arrow in C.arrows:
                    if arrow.source == other_apex and arrow.target == prod_obj:
                        # Check if this arrow makes the diagram commute
                        try:
                            comp1 = C.compose(proj1, arrow.name)
                            comp2 = C.compose(proj2, arrow.name)
                            
                            if comp1 == other_proj1 and comp2 == other_proj2:
                                if factorization is None:
                                    factorization = arrow.name
                                else:
                                    # Non-unique factorization
                                    is_universal = False
                                    break
                        except (KeyError, TypeError):
                            # Composition not defined or ill-typed
                            continue
                
                if factorization is None:
                    # No factorization found
                    is_universal = False
                    break
        
        if is_universal:
            return Limit(cone)
    
    return None


def equalizer(C: Cat, f: str, g: str) -> Optional[Limit]:
    """Find the equalizer of two parallel morphisms f, g: A → B.
    
    Returns None if the equalizer doesn't exist.
    """
    # Validate inputs
    f_arrow = None
    g_arrow = None
    
    for arrow in C.arrows:
        if arrow.name == f:
            f_arrow = arrow
        if arrow.name == g:
            g_arrow = arrow
    
    if f_arrow is None:
        raise ValueError(f"Morphism {f} not found in category")
    if g_arrow is None:
        raise ValueError(f"Morphism {g} not found in category")
    
    # Check that f and g are parallel
    if f_arrow.source != g_arrow.source or f_arrow.target != g_arrow.target:
        raise ValueError(f"Morphisms {f} and {g} are not parallel")
    
    source_obj = f_arrow.source
    target_obj = f_arrow.target
    
    # If f = g, then any object with a morphism to source is an equalizer
    if f == g:
        # The identity on source is the equalizer
        return Limit(Cone(source_obj, {source_obj: C.identity(source_obj)}))
    
    # Look for equalizer candidates
    obj_names = {obj.name for obj in C.objects}
    
    for eq_obj in obj_names:
        # Find morphisms from eq_obj to source_obj
        eq_morphisms = []
        
        for arrow in C.arrows:
            if arrow.source == eq_obj and arrow.target == source_obj:
                # Check if composing with f and g gives the same result
                try:
                    comp_f = C.compose(f, arrow.name)
                    comp_g = C.compose(g, arrow.name)
                    
                    if comp_f == comp_g:
                        eq_morphisms.append(arrow.name)
                except (KeyError, TypeError):
                    # Composition not defined or ill-typed
                    continue
        
        # Check if any of these morphisms is universal
        for eq_morph in eq_morphisms:
            cone = Cone(eq_obj, {source_obj: eq_morph})
            
            # Check universality
            is_universal = True
            
            for other_obj in obj_names:
                if other_obj == eq_obj:
                    continue
                
                # Find morphisms from other_obj that equalize f and g
                other_equalizers = []
                
                for arrow in C.arrows:
                    if arrow.source == other_obj and arrow.target == source_obj:
                        try:
                            comp_f = C.compose(f, arrow.name)
                            comp_g = C.compose(g, arrow.name)
                            
                            if comp_f == comp_g:
                                other_equalizers.append(arrow.name)
                        except (KeyError, TypeError):
                            continue
                
                # For each equalizing morphism, check unique factorization
                for other_eq in other_equalizers:
                    factorization = None
                    
                    for arrow in C.arrows:
                        if arrow.source == other_obj and arrow.target == eq_obj:
                            try:
                                comp = C.compose(eq_morph, arrow.name)
                                if comp == other_eq:
                                    if factorization is None:
                                        factorization = arrow.name
                                    else:
                                        # Non-unique factorization
                                        is_universal = False
                                        break
                            except (KeyError, TypeError):
                                continue
                    
                    if factorization is None:
                        # No factorization found
                        is_universal = False
                        break
                
                if not is_universal:
                    break
            
            if is_universal:
                return Limit(cone)
    
    return None


def terminal_object(C: Cat) -> Optional[str]:
    """Find the terminal object in category C.
    
    Returns the name of the terminal object, or None if it doesn't exist.
    """
    obj_names = {obj.name for obj in C.objects}
    
    for candidate in obj_names:
        is_terminal = True
        
        # Check that every object has exactly one morphism to candidate
        for source_obj in obj_names:
            morphisms_to_candidate = []
            
            for arrow in C.arrows:
                if arrow.source == source_obj and arrow.target == candidate:
                    morphisms_to_candidate.append(arrow.name)
            
            if len(morphisms_to_candidate) != 1:
                is_terminal = False
                break
        
        if is_terminal:
            return candidate
    
    return None


def initial_object(C: Cat) -> Optional[str]:
    """Find the initial object in category C.
    
    Returns the name of the initial object, or None if it doesn't exist.
    """
    obj_names = {obj.name for obj in C.objects}
    
    for candidate in obj_names:
        is_initial = True
        
        # Check that candidate has exactly one morphism to every object
        for target_obj in obj_names:
            morphisms_from_candidate = []
            
            for arrow in C.arrows:
                if arrow.source == candidate and arrow.target == target_obj:
                    morphisms_from_candidate.append(arrow.name)
            
            if len(morphisms_from_candidate) != 1:
                is_initial = False
                break
        
        if is_initial:
            return candidate
    
    return None


__all__ = [
    "Cone",
    "Limit", 
    "product",
    "equalizer",
    "terminal_object",
    "initial_object",
]
