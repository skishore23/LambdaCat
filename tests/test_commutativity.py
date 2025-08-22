import pytest

from LambdaCat.core import Cat, arrow, build_presentation, obj
from LambdaCat.core.ops_category import check_commutativity, paths


@pytest.mark.laws
def test_triangle_commutativity():
    """Test the triangle example (g∘f = h) from Phase 2 acceptance criteria."""
    # Build a category with triangle: A --f--> B --g--> C and A --h--> C
    A, B, C = obj("A"), obj("B"), obj("C")
    f = arrow("f", "A", "B")
    g = arrow("g", "B", "C")
    h = arrow("h", "A", "C")

    p = build_presentation((A, B, C), (f, g, h))
    C_cat = Cat.from_presentation(p)

    # Add composition: g∘f = h (note: g∘f means compose g with f, so (g,f) key)
    C_cat.composition[("g", "f")] = "h"

    # Get paths from A to C
    ps = paths(C_cat, "A", "C", max_length=2)
    assert len(ps) >= 2  # Should have at least [h] and [f, g] (note order)

    # Check commutativity
    report = check_commutativity(C_cat, "A", "C", ps)
    assert report.ok, f"Triangle should commute: {report.to_text()}"

    # Verify the specific paths
    assert ["h"] in ps  # direct path
    # Note: paths function returns [f, g] for A->B->C, but composition is stored as (g,f)
    assert any(len(p) == 2 for p in ps), f"Expected 2-length path, got: {ps}"


@pytest.mark.laws
def test_triangle_mismatch():
    """Test that mismatched triangles produce proper error reports."""
    # Build a category with triangle: A --f--> B --g--> C and A --h--> C
    A, B, C = obj("A"), obj("B"), obj("C")
    f = arrow("f", "A", "B")
    g = arrow("g", "B", "C")
    h = arrow("h", "A", "C")

    p = build_presentation((A, B, C), (f, g, h))
    Cat.from_presentation(p)

    # Add WRONG composition: g∘f ≠ h but both end at C
    # Create a new arrow that ends at C but is different from h
    wrong_arrow = arrow("wrong", "A", "C")
    p2 = build_presentation((A, B, C), (f, g, h, wrong_arrow))
    C_cat2 = Cat.from_presentation(p2)
    C_cat2.composition[("g", "f")] = "wrong"  # g∘f = wrong ≠ h

    # Get paths from A to C
    ps = paths(C_cat2, "A", "C", max_length=2)

    # Check commutativity - should fail
    report = check_commutativity(C_cat2, "A", "C", ps)
    assert not report.ok, "Mismatched triangle should not commute"
    assert "paths do not agree" in report.to_text()
    assert report.mismatch is not None
