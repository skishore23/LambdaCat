from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Generic, Iterable, List, Optional, Protocol, Sequence, Tuple, TypeVar, Union, runtime_checkable

T = TypeVar("T")

# Type aliases for better type safety
WitnessValue = Union[str, int, float, bool, None, "T"]
WitnessDict = Dict[str, WitnessValue]
ConfigValue = Union[str, int, float, bool, None, List["ConfigValue"], Dict[str, "ConfigValue"]]
ConfigDict = Dict[str, ConfigValue]


@runtime_checkable
class SupportsEq(Protocol):
	"""Protocol for objects that support equality comparison."""
	def __eq__(self, other: object) -> bool: ...


@dataclass(frozen=True)
class Violation(Generic[T]):
	law: str
	message: str
	witness: WitnessDict
	severity: str = "error"  # "error" | "warn"


@dataclass(frozen=True)
class LawResult(Generic[T]):
	law: str
	passed: bool
	violations: Sequence[Violation[T]]


class Law(Protocol[T]):
	name: str
	tags: Sequence[str]
	def run(self, ctx: T, config: ConfigDict) -> LawResult[T]: ...


@dataclass(frozen=True)
class LawSuite(Generic[T]):
	name: str
	laws: Sequence[Law[T]]


@dataclass(frozen=True)
class SuiteReport(Generic[T]):
	suite: str
	results: Sequence[LawResult[T]]

	@property
	def ok(self) -> bool:
		return all(r.passed for r in self.results)

	def to_text(self) -> str:
		passed_count = sum(1 for r in self.results if r.passed)
		total_count = len(self.results)
		status_line = f"Suite {self.suite}: {'OK' if self.ok else 'FAIL'} (laws passed: {passed_count}/{total_count})"
		
		lines = [status_line]
		for r in self.results:
			status = "✓" if r.passed else "✗"
			lines.append(f"  [{status}] {r.law}")
			if not r.passed:
				for v in r.violations:
					lines.append(f"    • {v.severity.upper()} {v.message} | witness={v.witness}")
		return "\n".join(lines)


def run_suite(ctx: T, suite: LawSuite[T], *, config: Optional[ConfigDict] = None) -> SuiteReport[T]:
	cfg = config or {}
	return SuiteReport[T](suite=suite.name, results=[law.run(ctx, cfg) for law in suite.laws])


