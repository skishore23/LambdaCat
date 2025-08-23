"""Hom-set helpers for categories."""

from collections import defaultdict
from typing import Optional

from .category import Cat


def hom(C: Cat, X: str, Y: str) -> list[str]:
    """Get all arrows from X to Y in category C."""
    arrows = []
    for arrow in C.arrows:
        if arrow.source == X and arrow.target == Y:
            arrows.append(arrow.name)
    return arrows


def is_iso(C: Cat, f: str) -> bool:
    """Check if arrow f is an isomorphism.

    An arrow f: A → B is iso if there exists g: B → A
    where g∘f = id_A and f∘g = id_B.
    """
    # Find the arrow
    f_arrow = None
    for arrow in C.arrows:
        if arrow.name == f:
            f_arrow = arrow
            break

    if f_arrow is None:
        raise KeyError(f"Arrow '{f}' not found in category")

    # Look for inverse
    A, B = f_arrow.source, f_arrow.target
    id_A = C.identities[A]
    id_B = C.identities[B]

    # Check all arrows from B to A
    for g in hom(C, B, A):
        # Check if g∘f = id_A and f∘g = id_B
        try:
            if C.compose(g, f) == id_A and C.compose(f, g) == id_B:
                return True
        except (KeyError, TypeError):
            # Composition might not be defined
            continue

    return False


def iso_inverse(C: Cat, f: str) -> Optional[str]:
    """Find the inverse of an isomorphism.

    Args:
        C: The category
        f: Isomorphism arrow name

    Returns:
        Name of the inverse arrow, or None if f is not an isomorphism
    """
    # Find the arrow
    f_arrow = None
    for arrow in C.arrows:
        if arrow.name == f:
            f_arrow = arrow
            break

    if f_arrow is None:
        raise KeyError(f"Arrow '{f}' not found in category")

    A, B = f_arrow.source, f_arrow.target
    id_A = C.identities[A]
    id_B = C.identities[B]

    # Check all arrows from B to A
    for g in hom(C, B, A):
        try:
            if C.compose(g, f) == id_A and C.compose(f, g) == id_B:
                return g
        except (KeyError, TypeError):
            continue

    return None


def iso_classes(C: Cat) -> list[list[str]]:
    """Group objects by isomorphism classes.

    Objects are in the same class if there's an isomorphism between them.
    """
    # Track which objects are connected by isomorphisms
    iso_related = defaultdict(set)

    for arrow in C.arrows:
        if is_iso(C, arrow.name):
            iso_related[arrow.source].add(arrow.target)
            iso_related[arrow.target].add(arrow.source)

    # Every object is isomorphic to itself (via identity)
    for obj in C.objects:
        iso_related[obj.name].add(obj.name)

    # Find connected components
    visited = set()
    classes = []

    for obj in C.objects:
        if obj.name not in visited:
            # BFS to find all objects isomorphic to this one
            component = []
            queue = [obj.name]

            while queue:
                current = queue.pop(0)
                if current not in visited:
                    visited.add(current)
                    component.append(current)

                    # Add all related objects
                    for related in iso_related[current]:
                        if related not in visited:
                            queue.append(related)

            if component:
                classes.append(sorted(component))

    return classes
