"""Tests for the rewriting system."""


from LambdaCat.core import Formal1, arrow, build_presentation, obj
from LambdaCat.core.rewriting import (
    RewriteRule,
    equal_modulo_relations,
    normalize_with_rules,
    orient_relations,
)


def test_rewrite_rule_apply_at():
    """Test applying a rewrite rule at specific positions."""
    # Rule: f;g -> h
    rule = RewriteRule(Formal1(("f", "g")), Formal1(("h",)))

    # Apply at beginning
    expr = Formal1(("f", "g", "k"))
    result = rule.apply_at(expr, 0)
    assert result is not None
    assert result.factors == ("h", "k")

    # Apply in middle
    expr = Formal1(("a", "f", "g", "k"))
    result = rule.apply_at(expr, 1)
    assert result is not None
    assert result.factors == ("a", "h", "k")

    # No match - wrong position
    result = rule.apply_at(expr, 0)
    assert result is None

    # No match - out of bounds
    result = rule.apply_at(expr, 3)
    assert result is None


def test_rewrite_rule_apply_anywhere():
    """Test applying a rewrite rule anywhere in expression."""
    rule = RewriteRule(Formal1(("f", "g")), Formal1(("h",)))

    # Multiple possible positions - applies first match
    expr = Formal1(("f", "g", "f", "g"))
    result = rule.apply_anywhere(expr)
    assert result is not None
    assert result.factors == ("h", "f", "g")

    # No match
    expr = Formal1(("a", "b", "c"))
    result = rule.apply_anywhere(expr)
    assert result is None


def test_orient_relations():
    """Test orientation of relations into rewrite rules."""
    # Longer expressions rewrite to shorter
    rel1 = (Formal1(("f", "g", "h")), Formal1(("k",)))
    rules = orient_relations([rel1])
    assert len(rules) == 1
    assert rules[0].lhs.factors == ("f", "g", "h")
    assert rules[0].rhs.factors == ("k",)

    # Equal length - uses left-to-right
    rel2 = (Formal1(("a", "b")), Formal1(("c", "d")))
    rules = orient_relations([rel2])
    assert len(rules) == 1
    assert rules[0].lhs.factors == ("a", "b")
    assert rules[0].rhs.factors == ("c", "d")


def test_normalize_with_rules():
    """Test normalization with multiple rules."""
    rules = [
        RewriteRule(Formal1(("f", "g")), Formal1(("h",))),
        RewriteRule(Formal1(("h", "k")), Formal1(("m",))),
    ]

    # Single step normalization
    expr = Formal1(("f", "g", "k"))
    normal = normalize_with_rules(expr, rules)
    assert normal.factors == ("m",)

    # Already in normal form
    expr = Formal1(("a", "b"))
    normal = normalize_with_rules(expr, rules)
    assert normal.factors == ("a", "b")

    # Max steps limit
    loop_rules = [
        RewriteRule(Formal1(("a",)), Formal1(("b",))),
        RewriteRule(Formal1(("b",)), Formal1(("a",))),
    ]
    expr = Formal1(("a",))
    normal = normalize_with_rules(expr, loop_rules, max_steps=5)
    # Should terminate after max_steps
    assert normal.factors in [("a",), ("b",)]


def test_equal_modulo_relations():
    """Test equality checking with relations."""
    # Create a presentation with relations
    A = obj("A")
    B = obj("B")
    C = obj("C")
    f = arrow("f", "A", "B")
    g = arrow("g", "B", "C")
    h = arrow("h", "A", "C")

    # Relation: f;g = h
    relations = [(Formal1(("f", "g")), Formal1(("h",)))]
    presentation = build_presentation([A, B, C], [f, g, h], relations)

    # Test equality
    p = Formal1(("f", "g"))
    q = Formal1(("h",))
    assert equal_modulo_relations(p, q, presentation)

    # Test with larger expression
    p = Formal1(("id:A", "f", "g", "id:C"))
    q = Formal1(("id:A", "h", "id:C"))
    assert equal_modulo_relations(p, q, presentation)

    # Test non-equal expressions
    p = Formal1(("f",))
    q = Formal1(("g",))
    assert not equal_modulo_relations(p, q, presentation)


def test_formal1_equal_method():
    """Test the equal method on Formal1."""
    # Create presentation with associativity relation
    A = obj("A")
    f = arrow("f", "A", "A")
    g = arrow("g", "A", "A")
    h = arrow("h", "A", "A")

    # (f;g);h = f;(g;h)
    lhs = Formal1(("f", "g", "h"))  # Implicitly right-associated
    rhs = Formal1(("f", "g", "h"))  # Same expression

    presentation = build_presentation([A], [f, g, h], [])

    # Syntactic equality
    assert lhs.equal(rhs, presentation)

    # With relation
    fg = arrow("fg", "A", "A")
    arrow("gh", "A", "A")
    rel_lhs = Formal1(("f", "g"))
    rel_rhs = Formal1(("fg",))

    presentation2 = build_presentation([A], [f, g, fg], [(rel_lhs, rel_rhs)])
    assert rel_lhs.equal(rel_rhs, presentation2)
