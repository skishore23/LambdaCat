from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Sequence, TypeVar, cast

from .laws import Law, LawResult, Violation, LawSuite, ConfigDict, WitnessDict, SupportsEq
from .fp.typeclasses import MonadT

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
M = TypeVar("M", bound=MonadT)


@dataclass(frozen=True)
class _MonadLeftIdentityLaw(Law[MonadT]):
    name: str = "monad-left-identity"
    tags: Sequence[str] = ("monad", "core")

    def run(self, monad: MonadT, config: ConfigDict) -> LawResult[MonadT]:
        violations: List[Violation[MonadT]] = []
        
        # Test left identity law: return a >>= f = f a
        try:
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", cast(WitnessDict, {"monad": str(monad)}))
                ])
            
            # Define test function
            f = lambda x: type(monad).pure(x + 1)
            
            # Test both sides
            left = type(monad).pure(test_value).bind(f)
            right = f(test_value)
            
            # Check equality using protocol
            if isinstance(left, SupportsEq) and isinstance(right, SupportsEq):
                if left != right:
                    violations.append(Violation(
                        self.name,
                        "return a >>= f ≠ f a",
                        cast(WitnessDict, {"monad": str(monad), "left": str(left), "right": str(right)})
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name,
                f"Error testing left identity law: {e}",
                cast(WitnessDict, {"monad": str(monad), "error": str(e)})
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _MonadRightIdentityLaw(Law[MonadT]):
    name: str = "monad-right-identity"
    tags: Sequence[str] = ("monad", "core")

    def run(self, monad: MonadT, config: ConfigDict) -> LawResult[MonadT]:
        violations: List[Violation[MonadT]] = []
        
        # Test right identity law: m >>= return = m
        try:
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", cast(WitnessDict, {"monad": str(monad)}))
                ])
            
            # Test both sides
            left = monad.bind(type(monad).pure)
            right = monad
            
            # Check equality using protocol
            if isinstance(left, SupportsEq) and isinstance(right, SupportsEq):
                if left != right:
                    violations.append(Violation(
                        self.name,
                        "m >>= return ≠ m",
                        cast(WitnessDict, {"monad": str(monad), "left": str(left), "right": str(right)})
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name,
                f"Error testing right identity law: {e}",
                cast(WitnessDict, {"monad": str(monad), "error": str(e)})
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


@dataclass(frozen=True)
class _MonadAssociativityLaw(Law[MonadT]):
    name: str = "monad-associativity"
    tags: Sequence[str] = ("monad", "core")

    def run(self, monad: MonadT, config: ConfigDict) -> LawResult[MonadT]:
        violations: List[Violation[MonadT]] = []
        
        # Test associativity law: (m >>= f) >>= g = m >>= (\x -> f x >>= g)
        try:
            test_value = config.get("test_value")
            if test_value is None:
                return LawResult(self.name, passed=False, violations=[
                    Violation(self.name, "No test_value provided in config", cast(WitnessDict, {"monad": str(monad)}))
                ])
            
            # Define test functions
            f = lambda x: type(monad).pure(x + 1)
            g = lambda x: type(monad).pure(x * 2)
            
            # Test both sides
            left = monad.bind(f).bind(g)
            right = monad.bind(lambda x: f(x).bind(g))
            
            # Check equality using protocol
            if isinstance(left, SupportsEq) and isinstance(right, SupportsEq):
                if left != right:
                    violations.append(Violation(
                        self.name,
                        "(m >>= f) >>= g ≠ m >>= (\\x -> f x >>= g)",
                        cast(WitnessDict, {"monad": str(monad), "left": str(left), "right": str(right)})
                    ))
        except Exception as e:
            violations.append(Violation(
                self.name,
                f"Error testing associativity law: {e}",
                cast(WitnessDict, {"monad": str(monad), "error": str(e)})
            ))
        
        return LawResult(self.name, passed=(len(violations) == 0), violations=violations)


MONAD_SUITE = LawSuite[MonadT]("monad", laws=[
    _MonadLeftIdentityLaw(),
    _MonadRightIdentityLaw(),
    _MonadAssociativityLaw()
])
