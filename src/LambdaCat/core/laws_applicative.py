from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Sequence, TypeVar

from .laws import Law, LawResult, Violation, LawSuite
from .fp.typeclasses import ApplicativeT

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
F = TypeVar("F", bound=ApplicativeT)


@dataclass(frozen=True)
class _ApplicativeIdentityLaw(Law[ApplicativeT]):
    name: str = "applicative-identity"
    tags: Sequence[str] = ("applicative", "core")

    def run(self, applicative: ApplicativeT, config: Dict[str, Any]) -> LawResult[ApplicativeT]:
        violations: List[Violation[ApplicativeT]] = []
        
        # Test identity law: pure id <*> v = v
        try:
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", {"applicative": applicative})
                ])
            
            # Create pure id
            pure_id = type(applicative).pure(lambda x: x)
            
            # Apply to test value: pure id <*> v = v
            result = pure_id.ap(applicative)
            
            # Check equality if possible
            if hasattr(result, '__eq__') and hasattr(applicative, '__eq__'):
                if result != applicative:
                    violations.append(Violation(
                        self.name,
                        "pure id <*> v ≠ v",
                        {"applicative": applicative, "result": result}
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name,
                f"Error testing identity law: {e}",
                {"applicative": applicative, "error": str(e)}
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _ApplicativeCompositionLaw(Law[ApplicativeT]):
    name: str = "applicative-composition"
    tags: Sequence[str] = ("applicative", "core")

    def run(self, applicative: ApplicativeT, config: Dict[str, Any]) -> LawResult[ApplicativeT]:
        violations: List[Violation[ApplicativeT]] = []
        
        # Test composition law: pure (.) <*> u <*> v <*> w = u <*> (v <*> w)
        try:
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", {"applicative": applicative})
                ])
            
            # Create test functions and values
            f = lambda x: x + 1
            g = lambda x: x * 2
            
            # Create pure composition function
            def compose_fn(f):
                return lambda g: lambda x: f(g(x))
            
            pure_comp = type(applicative).pure(compose_fn)
            
            # Test composition law: pure (.) <*> u <*> v <*> w = u <*> (v <*> w)
            # Left side: pure (.) <*> u <*> v <*> w
            u = type(applicative).pure(f)
            v = type(applicative).pure(g)
            w = applicative
            
            left = pure_comp.ap(u).ap(v).ap(w)
            
            # Right side: u <*> (v <*> w)
            right = u.ap(v.ap(w))
            
            # Check equality if possible
            if hasattr(left, '__eq__') and hasattr(right, '__eq__'):
                if left != right:
                    violations.append(Violation(
                        self.name,
                        "pure (.) <*> u <*> v <*> w ≠ u <*> (v <*> w)",
                        {"applicative": applicative, "left": left, "right": right}
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name,
                f"Error testing composition law: {e}",
                {"applicative": applicative, "error": str(e)}
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _ApplicativeHomomorphismLaw(Law[ApplicativeT]):
    name: str = "applicative-homomorphism"
    tags: Sequence[str] = ("applicative", "core")

    def run(self, applicative: ApplicativeT, config: Dict[str, Any]) -> LawResult[ApplicativeT]:
        violations: List[Violation[ApplicativeT]] = []
        
        # Test homomorphism law: pure f <*> pure x = pure (f x)
        try:
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", {"applicative": applicative})
                ])
            
            # Define test function and value
            f = lambda x: x + 1
            x = test_value
            
            # Test both sides
            left = type(applicative).pure(f).ap(type(applicative).pure(x))
            right = type(applicative).pure(f(x))
            
            # Check equality if possible
            if hasattr(left, '__eq__') and hasattr(right, '__eq__'):
                if left != right:
                    violations.append(Violation(
                        self.name,
                        "pure f <*> pure x ≠ pure (f x)",
                        {"applicative": applicative, "left": left, "right": right}
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name,
                f"Error testing homomorphism law: {e}",
                {"applicative": applicative, "error": str(e)}
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


APPLICATIVE_SUITE = LawSuite[ApplicativeT]("applicative", laws=[
    _ApplicativeIdentityLaw(),
    _ApplicativeCompositionLaw(),
    _ApplicativeHomomorphismLaw()
])
