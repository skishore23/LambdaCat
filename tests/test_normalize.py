"""Tests for the normalize function."""

import pytest

from src.LambdaCat.core import Cat, Formal1, arrow, build_presentation, normalize, obj, simplex


def test_normalize_single_arrow():
    """Test normalize with a single arrow."""
    # Create a simple category A -> B
    A = obj("A")
    B = obj("B")
    f = arrow("f", "A", "B")

    presentation = build_presentation([A, B], [f])
    C = Cat.from_presentation(presentation)

    # Single factor path
    path = Formal1(("f",))
    result = normalize(C, path)
    assert result == "f"


def test_normalize_composition():
    """Test normalize with composition of arrows."""
    # Create category A -> B -> C
    A = obj("A")
    B = obj("B")
    C_obj = obj("C")
    f = arrow("f", "A", "B")
    g = arrow("g", "B", "C")

    presentation = build_presentation([A, B, C_obj], [f, g])
    C = Cat.from_presentation(presentation)

    # Add composition
    C.composition[("g", "f")] = "g∘f"

    # Path [f, g] should normalize to g∘f
    path = Formal1(("f", "g"))
    result = normalize(C, path)
    assert result == "g∘f"


def test_normalize_with_identity():
    """Test normalize with identity morphisms."""
    # Create a simple category
    A = obj("A")
    f = arrow("f", "A", "A")

    presentation = build_presentation([A], [f])
    C = Cat.from_presentation(presentation)

    # Path with identity
    path = Formal1(("id:A", "f"))
    result = normalize(C, path)
    assert result == "f"

    path2 = Formal1(("f", "id:A"))
    result2 = normalize(C, path2)
    assert result2 == "f"


def test_normalize_simplex():
    """Test normalize in a simplex category."""
    Delta2 = simplex(2)

    # Path 0->1->2 should normalize to 0->2
    path = Formal1(("0->1", "1->2"))
    result = normalize(Delta2, path)
    assert result == "0->2"

    # Path with identity
    path2 = Formal1(("0->1", "id:1"))
    result2 = normalize(Delta2, path2)
    assert result2 == "0->1"


def test_normalize_associativity():
    """Test that normalize handles associativity correctly."""
    # Create category A -> B -> C -> D
    A = obj("A")
    B = obj("B")
    C_obj = obj("C")
    D = obj("D")
    f = arrow("f", "A", "B")
    g = arrow("g", "B", "C")
    h = arrow("h", "C", "D")
    gf = arrow("g∘f", "A", "C")
    hg = arrow("h∘g", "B", "D")
    hgf = arrow("h∘g∘f", "A", "D")

    presentation = build_presentation([A, B, C_obj, D], [f, g, h, gf, hg, hgf])
    C = Cat.from_presentation(presentation)

    # Add compositions
    C.composition[("g", "f")] = "g∘f"
    C.composition[("h", "g")] = "h∘g"
    C.composition[("h", "g∘f")] = "h∘g∘f"
    C.composition[("h∘g", "f")] = "h∘g∘f"

    # Path [f, g, h] should normalize to h∘g∘f
    path = Formal1(("f", "g", "h"))
    result = normalize(C, path)
    assert result == "h∘g∘f"


def test_normalize_empty_path_error():
    """Test that normalize raises error for empty path."""
    C = simplex(1)
    empty_path = Formal1(())

    with pytest.raises(ValueError, match="empty path"):
        normalize(C, empty_path)


def test_normalize_invalid_composition_error():
    """Test that normalize raises error for invalid composition."""
    # Create disconnected category
    A = obj("A")
    B = obj("B")
    f = arrow("f", "A", "A")
    g = arrow("g", "B", "B")

    presentation = build_presentation([A, B], [f, g])
    C = Cat.from_presentation(presentation)

    # Try to compose arrows that don't compose
    path = Formal1(("f", "g"))

    with pytest.raises(TypeError):
        normalize(C, path)


def test_normalize_unknown_arrow_error():
    """Test that normalize raises error for unknown arrow."""
    C = simplex(1)

    # Path with multiple arrows where second is unknown
    path = Formal1(("0->1", "unknown"))

    # Arrow lookup will fail in compose
    with pytest.raises(KeyError, match="Arrow 'unknown' not found"):
        normalize(C, path)
