"""Term rewriting for categorical expressions."""

from collections.abc import Sequence
from typing import Optional

from .presentation import Formal1, Presentation


class RewriteRule:
    """A rewrite rule that transforms lhs into rhs."""

    def __init__(self, lhs: Formal1, rhs: Formal1):
        self.lhs = lhs
        self.rhs = rhs

    def apply_at(self, expr: Formal1, position: int) -> Optional[Formal1]:
        """Apply this rule starting at the given position.

        Returns the rewritten expression on success, None if the rule doesn't match.
        """
        lhs_len = len(self.lhs.factors)
        if position + lhs_len > len(expr.factors):
            return None

        # Check if the pattern matches
        for i in range(lhs_len):
            if expr.factors[position + i] != self.lhs.factors[i]:
                return None

        new_factors = (
            expr.factors[:position] +
            self.rhs.factors +
            expr.factors[position + lhs_len:]
        )
        return Formal1(new_factors)

    def apply_anywhere(self, expr: Formal1) -> Optional[Formal1]:
        """Apply this rule at the first position where it matches.

        Returns the rewritten expression, or None if no match found.
        """
        for i in range(len(expr.factors)):
            result = self.apply_at(expr, i)
            if result is not None:
                return result
        return None


def orient_relations(relations: Sequence[tuple[Formal1, Formal1]]) -> list[RewriteRule]:
    """Convert relations into rewrite rules.

    Uses a heuristic: prefer longer expressions on the left (to simplify),
    otherwise use left-to-right orientation.
    """
    rules = []
    for lhs, rhs in relations:
        # Orient by length to reduce complexity
        if len(lhs.factors) > len(rhs.factors):
            rules.append(RewriteRule(lhs, rhs))
        elif len(rhs.factors) > len(lhs.factors):
            rules.append(RewriteRule(rhs, lhs))
        else:
            # Same length - use left-to-right
            rules.append(RewriteRule(lhs, rhs))
    return rules


def normalize_with_rules(expr: Formal1, rules: list[RewriteRule], max_steps: int = 100) -> Formal1:
    """Normalize an expression by repeatedly applying rewrite rules.

    Applies rules until no more rules apply (normal form) or max_steps is reached.
    """
    current = expr
    steps = 0

    while steps < max_steps:
        # Try each rule
        applied = False
        for rule in rules:
            result = rule.apply_anywhere(current)
            if result is not None:
                current = result
                applied = True
                break

        if not applied:
            # No rule applied - we're in normal form
            break

        steps += 1

    return current


def equal_modulo_relations(p: Formal1, q: Formal1, presentation: Presentation) -> bool:
    """Check if two expressions are equal modulo the presentation's relations.

    Uses rewriting to normalize both expressions and compares normal forms.
    """
    # Syntactic equality
    if p.factors == q.factors:
        return True

    # No relations - only syntactic equality
    if not presentation.relations:
        return False

    # Orient relations into rewrite rules
    rules = orient_relations(presentation.relations)

    # Normalize both expressions
    p_normal = normalize_with_rules(p, rules)
    q_normal = normalize_with_rules(q, rules)

    # Compare normal forms
    return p_normal.factors == q_normal.factors
