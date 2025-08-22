from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Sequence, TypeVar, cast

from .laws import Law, LawResult, Violation, LawSuite, ConfigDict, WitnessDict, SupportsEq
from .fp.typeclasses import FunctorT

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
F = TypeVar("F", bound=FunctorT)


@dataclass(frozen=True)
class _FunctorIdentityLaw(Law[FunctorT]):
    name: str = "functor-identity"
    tags: Sequence[str] = ("functor", "core")

    def run(self, functor: FunctorT, config: ConfigDict) -> LawResult[FunctorT]:
        violations: List[Violation[FunctorT]] = []
        
        # Test identity law: fmap id = id
        try:
            # Create a test value
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", cast(WitnessDict, {"functor": str(functor)}))
                ])
            
            # Apply identity function
            result = functor.map(lambda x: x)
            
            # Check if result equals original (for simple cases)
            if isinstance(result, SupportsEq):
                if result != functor:
                    violations.append(Violation(
                        self.name, 
                        "fmap id ≠ id", 
                        cast(WitnessDict, {"functor": str(functor), "result": str(result)})
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name, 
                f"Error testing identity law: {e}", 
                cast(WitnessDict, {"functor": str(functor), "error": str(e)})
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _FunctorCompositionLaw(Law[FunctorT]):
    name: str = "functor-composition"
    tags: Sequence[str] = ("functor", "core")

    def run(self, functor: FunctorT, config: ConfigDict) -> LawResult[FunctorT]:
        violations: List[Violation[FunctorT]] = []
        
        # Test composition law: fmap (g . f) = fmap g . fmap f
        try:
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", cast(WitnessDict, {"functor": str(functor)}))
                ])
            
            # Define test functions
            f = lambda x: x + 1
            g = lambda x: x * 2
            
            # Test: fmap (g . f) = fmap g . fmap f
            composed = functor.map(lambda x: g(f(x)))
            separate = functor.map(f).map(g)
            
            # Check equality if possible
            if isinstance(composed, SupportsEq) and isinstance(separate, SupportsEq):
                if composed != separate:
                    violations.append(Violation(
                        self.name,
                        "fmap (g . f) ≠ fmap g . fmap f",
                        cast(WitnessDict, {"functor": str(functor), "composed": str(composed), "separate": str(separate)})
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name,
                f"Error testing composition law: {e}",
                cast(WitnessDict, {"functor": str(functor), "error": str(e)})
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


FUNCTOR_SUITE = LawSuite[FunctorT]("functor", laws=[
    _FunctorIdentityLaw(),
    _FunctorCompositionLaw()
])


