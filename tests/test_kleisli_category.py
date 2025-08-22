from __future__ import annotations

from LambdaCat.core.fp.kleisli import kleisli_category
from LambdaCat.core.laws import run_suite
from LambdaCat.core.laws_category import CATEGORY_SUITE


def test_kleisli_structural_category_laws() -> None:
    # Small graph: A -f-> B -g-> C with composition h = g∘f
    objects = ("A", "B", "C")
    morphisms = {
        "id:A": ("A", "A"),
        "id:B": ("B", "B"),
        "id:C": ("C", "C"),
        "f": ("A", "B"),
        "g": ("B", "C"),
        "h": ("A", "C"),
    }
    composition = {
        ("id:A", "id:A"): "id:A",
        ("id:B", "id:B"): "id:B",
        ("id:C", "id:C"): "id:C",
        ("f", "id:A"): "f",
        ("id:B", "f"): "f",
        ("g", "id:B"): "g",
        ("id:C", "g"): "g",
        ("g", "f"): "h",
        ("id:C", "h"): "h",
        ("h", "id:A"): "h",
    }
    C = kleisli_category("KlM-struct", objects, morphisms, composition)
    report = run_suite(C, CATEGORY_SUITE)
    assert report.ok, report.to_text()


