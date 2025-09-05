"""Tests for hom-set helpers."""

import pytest

from src.LambdaCat.core import (
    discrete,
    hom,
    is_iso,
    iso_classes,
    iso_inverse,
    simplex,
    walking_isomorphism,
)


def test_hom_basic():
    """Test basic hom-set functionality."""
    # Walking isomorphism: A ⇄ B
    C = walking_isomorphism()

    # Test hom-sets
    assert set(hom(C, "A", "B")) == {"f"}
    assert set(hom(C, "B", "A")) == {"g"}
    assert set(hom(C, "A", "A")) == {"id:A"}
    assert set(hom(C, "B", "B")) == {"id:B"}


def test_hom_empty():
    """Test empty hom-sets."""
    # Discrete category with disconnected objects
    C = discrete(["A", "B"])

    # No non-identity arrows
    assert hom(C, "A", "B") == []
    assert hom(C, "B", "A") == []
    assert hom(C, "A", "A") == ["id:A"]
    assert hom(C, "B", "B") == ["id:B"]


def test_hom_simplex():
    """Test hom-sets in simplex category."""
    C = simplex(2)  # 0 → 1 → 2

    # Check various hom-sets
    assert hom(C, "0", "0") == ["id:0"]
    assert hom(C, "0", "1") == ["0->1"]
    assert hom(C, "0", "2") == ["0->2"]
    assert hom(C, "1", "0") == []  # No arrows backwards
    assert hom(C, "1", "1") == ["id:1"]
    assert hom(C, "1", "2") == ["1->2"]


def test_is_iso_walking_isomorphism():
    """Test isomorphism detection in walking isomorphism."""
    C = walking_isomorphism()

    # f and g are isomorphisms
    assert is_iso(C, "f")
    assert is_iso(C, "g")

    # Identities are isomorphisms
    assert is_iso(C, "id:A")
    assert is_iso(C, "id:B")


def test_is_iso_simplex():
    """Test isomorphism detection in simplex category."""
    C = simplex(2)

    # Only identities are isomorphisms in simplex
    assert is_iso(C, "id:0")
    assert is_iso(C, "id:1")
    assert is_iso(C, "id:2")

    # Non-identity arrows are not isomorphisms
    assert not is_iso(C, "0->1")
    assert not is_iso(C, "1->2")
    assert not is_iso(C, "0->2")


def test_is_iso_discrete():
    """Test isomorphism detection in discrete category."""
    C = discrete(["A", "B", "C"])

    # Only identities exist, and they are isomorphisms
    assert is_iso(C, "id:A")
    assert is_iso(C, "id:B")
    assert is_iso(C, "id:C")


def test_is_iso_unknown_arrow():
    """Test isomorphism check with unknown arrow."""
    C = discrete(["A"])

    with pytest.raises(KeyError, match="Arrow 'unknown' not found"):
        is_iso(C, "unknown")


def test_iso_inverse():
    """Test finding inverse of isomorphisms."""
    C = walking_isomorphism()

    # f and g are inverses
    assert iso_inverse(C, "f") == "g"
    assert iso_inverse(C, "g") == "f"

    # Identities are their own inverses
    assert iso_inverse(C, "id:A") == "id:A"
    assert iso_inverse(C, "id:B") == "id:B"


def test_iso_inverse_non_iso():
    """Test inverse finding for non-isomorphisms."""
    C = simplex(2)

    # Non-identity arrows have no inverse
    assert iso_inverse(C, "0->1") is None
    assert iso_inverse(C, "1->2") is None
    assert iso_inverse(C, "0->2") is None

    # Identities are their own inverses
    assert iso_inverse(C, "id:0") == "id:0"
    assert iso_inverse(C, "id:1") == "id:1"
    assert iso_inverse(C, "id:2") == "id:2"


def test_iso_classes_walking_isomorphism():
    """Test isomorphism classes in walking isomorphism."""
    C = walking_isomorphism()

    classes = iso_classes(C)

    # A and B are isomorphic
    assert len(classes) == 1
    assert set(classes[0]) == {"A", "B"}


def test_iso_classes_discrete():
    """Test isomorphism classes in discrete category."""
    C = discrete(["A", "B", "C"])

    classes = iso_classes(C)

    # Each object is in its own isomorphism class
    assert len(classes) == 3
    class_sets = [set(cls) for cls in classes]
    assert {"A"} in class_sets
    assert {"B"} in class_sets
    assert {"C"} in class_sets


def test_iso_classes_simplex():
    """Test isomorphism classes in simplex category."""
    C = simplex(2)

    classes = iso_classes(C)

    # Each object is in its own class (no non-trivial isomorphisms)
    assert len(classes) == 3
    class_sets = [set(cls) for cls in classes]
    assert {"0"} in class_sets
    assert {"1"} in class_sets
    assert {"2"} in class_sets


def test_iso_classes_empty_category():
    """Test isomorphism classes in empty category."""
    C = discrete([])

    classes = iso_classes(C)
    assert classes == []
