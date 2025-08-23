"""Diagnostic tools for limits - help users understand failures."""

from dataclasses import dataclass
from typing import Optional

from .category import Cat
from .hom_helpers import hom


@dataclass(frozen=True)
class ProductFailure:
    """Explanation for why a product doesn't exist."""
    obj1: str
    obj2: str
    reason: str
    details: dict
    suggestion: Optional[str] = None


@dataclass(frozen=True)
class EqualizerFailure:
    """Explanation for why an equalizer doesn't exist."""
    f: str
    g: str
    reason: str
    details: dict
    suggestion: Optional[str] = None


def diagnose_product_failure(C: Cat, obj1: str, obj2: str) -> ProductFailure:
    """Figure out why a product doesn't exist and suggest how to fix it."""
    from .limits import product

    # Check if it actually does exist
    try:
        result = product(C, obj1, obj2)
        if result is not None:
            return ProductFailure(
                obj1, obj2,
                "Product actually exists",
                {"product": result},
                "No fix needed - product exists"
            )
    except Exception as e:
        return ProductFailure(
            obj1, obj2,
            "Invalid input",
            {"error": str(e)},
            "Check that both objects exist in the category"
        )

    # Analyze why product doesn't exist
    obj_names = {obj.name for obj in C.objects}

    # Check for potential product objects
    candidates = []
    for prod_obj in obj_names:
        proj1_arrows = hom(C, prod_obj, obj1)
        proj2_arrows = hom(C, prod_obj, obj2)

        if proj1_arrows and proj2_arrows:
            candidates.append({
                "object": prod_obj,
                "projections_to_obj1": proj1_arrows,
                "projections_to_obj2": proj2_arrows,
                "cone_count": len(proj1_arrows) * len(proj2_arrows)
            })

    if not candidates:
        # No object has arrows to both targets
        missing_arrows = []
        for obj in obj_names:
            to_obj1 = len(hom(C, obj, obj1)) > 0
            to_obj2 = len(hom(C, obj, obj2)) > 0
            if not (to_obj1 and to_obj2):
                missing_arrows.append({
                    "from": obj,
                    "missing_to_obj1": not to_obj1,
                    "missing_to_obj2": not to_obj2
                })

        return ProductFailure(
            obj1, obj2,
            "No candidate product objects",
            {
                "missing_arrows": missing_arrows,
                "total_objects": len(obj_names)
            },
            f"Add arrows from some object to both {obj1} and {obj2}"
        )

    # Candidates exist but none is universal
    # Check universality failures
    universality_failures = []

    for candidate in candidates:
        failures = []
        prod_obj = candidate["object"]

        # Check each potential cone from other objects
        for other_obj in obj_names:
            if other_obj == prod_obj:
                continue

            other_to_obj1 = hom(C, other_obj, obj1)
            other_to_obj2 = hom(C, other_obj, obj2)

            if other_to_obj1 and other_to_obj2:
                # This forms a cone - check if there's a unique morphism to candidate
                mediating_arrows = hom(C, other_obj, prod_obj)

                if not mediating_arrows:
                    failures.append({
                        "cone_apex": other_obj,
                        "issue": "no_mediating_arrow",
                        "description": f"No arrow from {other_obj} to {prod_obj}"
                    })
                elif len(mediating_arrows) > 1:
                    failures.append({
                        "cone_apex": other_obj,
                        "issue": "multiple_mediating_arrows",
                        "arrow_count": str(len(mediating_arrows)),
                        "description": f"Multiple arrows from {other_obj} to {prod_obj}: {mediating_arrows}"
                    })
                else:
                    # Check if composition works correctly
                    m = mediating_arrows[0]
                    proj1_candidates = candidate["projections_to_obj1"]
                    proj2_candidates = candidate["projections_to_obj2"]

                    composition_failures = []
                    for p1 in proj1_candidates:
                        for p2 in proj2_candidates:
                            try:
                                # Check if p1 ∘ m is in other_to_obj1
                                comp1 = C.compose(p1, m)
                                if comp1 not in other_to_obj1:
                                    composition_failures.append(f"{p1}∘{m} = {comp1} ∉ hom({other_obj}, {obj1})")

                                comp2 = C.compose(p2, m)
                                if comp2 not in other_to_obj2:
                                    composition_failures.append(f"{p2}∘{m} = {comp2} ∉ hom({other_obj}, {obj2})")

                            except (KeyError, TypeError) as e:
                                composition_failures.append(f"Composition error: {e}")

                    if composition_failures:
                        failures.append({
                            "cone_apex": other_obj,
                            "issue": "composition_mismatch",
                            "failure_count": str(len(composition_failures)),
                            "description": f"Composition failures: {composition_failures[:3]}..."  # Truncate for brevity
                        })

        if failures:
            universality_failures.append({
                "candidate": prod_obj,
                "failures": failures
            })

    return ProductFailure(
        obj1, obj2,
        "Candidates exist but none is universal",
        {
            "candidates": candidates,
            "universality_failures": universality_failures
        },
        "Fix composition tables or add missing arrows to make one candidate universal"
    )


def diagnose_equalizer_failure(C: Cat, f: str, g: str) -> EqualizerFailure:
    """Diagnose why an equalizer doesn't exist.

    Args:
        C: The category
        f, g: Parallel arrows for which equalizer is sought

    Returns:
        EqualizerFailure with explanation and suggestions
    """
    from .limits import equalizer

    # Find the arrows
    f_arrow = None
    g_arrow = None
    for arrow in C.arrows:
        if arrow.name == f:
            f_arrow = arrow
        if arrow.name == g:
            g_arrow = arrow

    if f_arrow is None:
        return EqualizerFailure(f, g, "Arrow not found", {"missing": f}, f"Add arrow '{f}' to category")

    if g_arrow is None:
        return EqualizerFailure(f, g, "Arrow not found", {"missing": g}, f"Add arrow '{g}' to category")

    # Check if they're parallel
    if f_arrow.source != g_arrow.source or f_arrow.target != g_arrow.target:
        return EqualizerFailure(
            f, g,
            "Arrows not parallel",
            {
                "f_type": f"{f_arrow.source} → {f_arrow.target}",
                "g_type": f"{g_arrow.source} → {g_arrow.target}"
            },
            "Equalizers require parallel arrows (same source and target)"
        )

    # Check if equalizer exists
    try:
        result = equalizer(C, f, g)
        if result is not None:
            return EqualizerFailure(
                f, g,
                "Equalizer actually exists",
                {"equalizer": result},
                "No fix needed - equalizer exists"
            )
    except Exception as e:
        return EqualizerFailure(
            f, g,
            "Error computing equalizer",
            {"error": str(e)},
            "Check category structure and composition table"
        )

    # Analyze why equalizer doesn't exist
    source = f_arrow.source
    target = f_arrow.target

    # Find objects with arrows to the source that equalize f and g
    equalizing_arrows = []

    for obj in C.objects:
        arrows_to_source = hom(C, obj.name, source)

        for h in arrows_to_source:
            try:
                fh = C.compose(f, h)
                gh = C.compose(g, h)

                if fh == gh:
                    equalizing_arrows.append({
                        "domain": obj.name,
                        "arrow": h,
                        "equalizes": f"{f}∘{h} = {g}∘{h} = {fh}"
                    })
            except (KeyError, TypeError):
                # Composition not defined
                continue

    if not equalizing_arrows:
        return EqualizerFailure(
            f, g,
            "No equalizing arrows found",
            {
                "parallel_pair": f"{source} ⇉ {target}",
                "checked_objects": len(C.objects)
            },
            f"Add an object E with arrow e: E → {source} such that {f}∘e = {g}∘e"
        )

    # Equalizing arrows exist but no universal one
    return EqualizerFailure(
        f, g,
        "Equalizing arrows exist but none is universal",
        {
            "equalizing_arrows": equalizing_arrows,
            "parallel_pair": f"{source} ⇉ {target}"
        },
        "Add a universal equalizing arrow (one that factors through all others)"
    )


def suggest_product_construction(C: Cat, obj1: str, obj2: str) -> dict:
    """Suggest how to add a product to the category.

    Returns a dictionary with suggested objects and arrows to add.
    """
    suggestion = {
        "add_object": f"{obj1}×{obj2}",
        "add_arrows": [
            {"name": "π₁", "source": f"{obj1}×{obj2}", "target": obj1, "description": "first projection"},
            {"name": "π₂", "source": f"{obj1}×{obj2}", "target": obj2, "description": "second projection"}
        ],
        "add_compositions": [],
        "reasoning": f"Standard categorical product construction for {obj1} and {obj2}"
    }

    # Add compositions with identities
    suggestion["add_compositions"].extend([
        {"compose": ("π₁", f"id:{obj1}×{obj2}"), "result": "π₁"},
        {"compose": ("π₂", f"id:{obj1}×{obj2}"), "result": "π₂"},
        {"compose": (f"id:{obj1}", "π₁"), "result": "π₁"},
        {"compose": (f"id:{obj2}", "π₂"), "result": "π₂"}
    ])

    return suggestion
