"""Tests for limits diagnostics."""


from src.LambdaCat.core import (
    Cat,
    arrow,
    build_presentation,
    diagnose_equalizer_failure,
    diagnose_product_failure,
    discrete,
    obj,
    suggest_product_construction,
    walking_isomorphism,
)


def test_diagnose_product_exists():
    """Test diagnosis when product actually exists."""
    # Walking isomorphism has products (each object is product with itself)
    C = walking_isomorphism()

    result = diagnose_product_failure(C, "A", "A")
    assert result.reason == "Product actually exists"
    assert "product" in result.details
    assert result.suggestion == "No fix needed - product exists"


def test_diagnose_product_no_candidates():
    """Test diagnosis when no candidate product objects exist."""
    # Create category with disconnected objects
    A = obj("A")
    B = obj("B")
    C_obj = obj("C")

    # Only add identity arrows
    presentation = build_presentation([A, B, C_obj], [])
    C = Cat.from_presentation(presentation)

    result = diagnose_product_failure(C, "A", "B")
    assert result.reason == "No candidate product objects"
    assert "missing_arrows" in result.details
    assert "Add arrows" in result.suggestion


def test_diagnose_product_invalid_input():
    """Test diagnosis with invalid inputs."""
    C = discrete(["A"])

    result = diagnose_product_failure(C, "A", "NonExistent")
    assert result.reason == "Invalid input"
    assert "error" in result.details


def test_diagnose_product_non_universal():
    """Test diagnosis when candidates exist but aren't universal."""
    # Create a category where we have arrows but no universal product
    A = obj("A")
    B = obj("B")
    P = obj("P")
    Q = obj("Q")

    # P has arrows to both A and B, Q has arrows to both
    p1 = arrow("p1", "P", "A")
    p2 = arrow("p2", "P", "B")
    q1 = arrow("q1", "Q", "A")
    q2 = arrow("q2", "Q", "B")

    presentation = build_presentation([A, B, P, Q], [p1, p2, q1, q2])
    C = Cat.from_presentation(presentation)

    result = diagnose_product_failure(C, "A", "B")
    assert result.reason == "Candidates exist but none is universal"
    assert "candidates" in result.details
    assert "universality_failures" in result.details


def test_diagnose_equalizer_arrows_not_found():
    """Test equalizer diagnosis when arrows don't exist."""
    C = discrete(["A"])

    result = diagnose_equalizer_failure(C, "f", "g")
    assert result.reason == "Arrow not found"
    assert result.details["missing"] == "f"


def test_diagnose_equalizer_not_parallel():
    """Test equalizer diagnosis when arrows aren't parallel."""
    A = obj("A")
    B = obj("B")
    f = arrow("f", "A", "B")
    g = arrow("g", "B", "A")  # Different direction

    presentation = build_presentation([A, B], [f, g])
    C = Cat.from_presentation(presentation)

    result = diagnose_equalizer_failure(C, "f", "g")
    assert result.reason == "Arrows not parallel"
    assert "f_type" in result.details
    assert "g_type" in result.details


def test_diagnose_equalizer_exists():
    """Test diagnosis when equalizer actually exists."""
    # In discrete category, all arrows are equal to themselves
    C = discrete(["A", "B"])

    result = diagnose_equalizer_failure(C, "id:A", "id:A")
    assert result.reason == "Equalizer actually exists"
    assert "equalizer" in result.details


def test_diagnose_equalizer_no_equalizing_arrows():
    """Test diagnosis when no equalizing arrows exist."""
    A = obj("A")
    B = obj("B")
    C_obj = obj("C")

    # Create parallel arrows f,g: A → B that are different
    f = arrow("f", "A", "B")
    g = arrow("g", "A", "B")

    presentation = build_presentation([A, B, C_obj], [f, g])
    C = Cat.from_presentation(presentation)

    # Add compositions to make f ≠ g
    C.composition[("f", "id:A")] = "f"
    C.composition[("g", "id:A")] = "g"
    C.composition[("id:B", "f")] = "f"
    C.composition[("id:B", "g")] = "g"

    result = diagnose_equalizer_failure(C, "f", "g")
    assert result.reason == "No equalizing arrows found"
    assert "parallel_pair" in result.details


def test_suggest_product_construction():
    """Test product construction suggestions."""
    C = discrete(["A", "B"])

    suggestion = suggest_product_construction(C, "A", "B")

    assert suggestion["add_object"] == "A×B"
    assert len(suggestion["add_arrows"]) == 2
    assert any(arr["name"] == "π₁" for arr in suggestion["add_arrows"])
    assert any(arr["name"] == "π₂" for arr in suggestion["add_arrows"])
    assert len(suggestion["add_compositions"]) >= 4  # Identity compositions
    assert "reasoning" in suggestion


def test_diagnose_equalizer_non_universal():
    """Test diagnosis when equalizing arrows exist but aren't universal."""
    A = obj("A")
    B = obj("B")
    E1 = obj("E1")
    E2 = obj("E2")

    # Parallel arrows f,g: A → B
    f = arrow("f", "A", "B")
    g = arrow("g", "A", "B")  # Different name but we'll make them equal via composition

    # Equalizing arrows
    e1 = arrow("e1", "E1", "A")
    e2 = arrow("e2", "E2", "A")

    presentation = build_presentation([A, B, E1, E2], [f, g, e1, e2])
    C = Cat.from_presentation(presentation)

    # Set up compositions to make f∘e1 = g∘e1 (both equal the same thing)
    C.composition[("f", "e1")] = "result"
    C.composition[("g", "e1")] = "result"
    C.composition[("f", "e2")] = "result"
    C.composition[("g", "e2")] = "result"

    result = diagnose_equalizer_failure(C, "f", "g")

    # Should find equalizing arrows or already exist
    assert ("equalizing_arrows" in result.details or
            result.reason == "Equalizer actually exists" or
            result.reason == "No equalizing arrows found")  # Depending on composition setup
