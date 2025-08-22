from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Protocol, Sequence, Tuple, TypeVar

from .typeclasses import ApplicativeT, FunctorT, MonadT

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


class Law(Protocol, Generic[A]):
	"""Protocol for laws that can be run on a context."""

	name: str
	tags: Sequence[str]

	def run(self, ctx: A, config: Dict[str, Any]) -> "LawResult[A]": ...


@dataclass(frozen=True)
class Violation(Generic[A]):
	"""A violation of a law."""

	law: str
	message: str
	witness: Dict[str, Any]


@dataclass(frozen=True)
class LawResult(Generic[A]):
	"""Result of running a law."""

	law_name: str
	passed: bool
	violations: Sequence[Violation[A]]


# -----------------------------
# Functor laws
# -----------------------------


@dataclass(frozen=True)
class FunctorIdentityLaw(Law[FunctorT[A]]):
	name: str = "functor.identity"
	tags: Sequence[str] = ("functor",)

	def run(self, ctx: FunctorT[A], config: Dict[str, Any]) -> LawResult[FunctorT[A]]:
		ok = ctx.map(lambda x: x) == ctx
		violations: Sequence[Violation[FunctorT[A]]] = () if ok else (
			Violation(law=self.name, message="f.map(id) != f", witness={"ctx": ctx}),
		)
		return LawResult(self.name, ok, violations)


@dataclass(frozen=True)
class FunctorCompositionLaw(Law[Tuple[FunctorT[A], Callable[[A], B], Callable[[B], C]]]):
	name: str = "functor.composition"
	tags: Sequence[str] = ("functor",)

	def run(self, ctx: Tuple[FunctorT[A], Callable[[A], B], Callable[[B], C]], config: Dict[str, Any]) -> LawResult[Tuple[FunctorT[A], Callable[[A], B], Callable[[B], C]]]:
		f, g, h = ctx
		compose = lambda x: h(g(x))
		ok = f.map(g).map(h) == f.map(compose)
		violations: Sequence[Violation[Tuple[FunctorT[A], Callable[[A], B], Callable[[B], C]]]] = () if ok else (
			Violation(law=self.name, message="f.map(g).map(h) != f.map(g . h)", witness={"f": f}),
		)
		return LawResult(self.name, ok, violations)


# -----------------------------
# Applicative laws
# -----------------------------


@dataclass(frozen=True)
class ApplicativeIdentityLaw(Law[ApplicativeT[A]]):
	name: str = "applicative.identity"
	tags: Sequence[str] = ("applicative",)

	def run(self, ctx: ApplicativeT[A], config: Dict[str, Any]) -> LawResult[ApplicativeT[A]]:
		cls = type(ctx)
		if not hasattr(cls, "pure"):
			return LawResult(self.name, False, (Violation(law=self.name, message="class has no pure method", witness={"ctx": ctx}),))
		lhs = ctx.ap(cls.pure(lambda x: x))
		ok = lhs == ctx
		violations: Sequence[Violation[ApplicativeT[A]]] = () if ok else (
			Violation(law=self.name, message="v.ap(pure(id)) != v", witness={"ctx": ctx}),
		)
		return LawResult(self.name, ok, violations)


@dataclass(frozen=True)
class ApplicativeHomomorphismLaw(Law[Tuple[type, Callable[[A], B], A]]):
	name: str = "applicative.homomorphism"
	tags: Sequence[str] = ("applicative",)

	def run(self, ctx: Tuple[type, Callable[[A], B], A], config: Dict[str, Any]) -> LawResult[Tuple[type, Callable[[A], B], A]]:
		cls, f, x = ctx
		if not hasattr(cls, "pure"):
			return LawResult(self.name, False, (Violation(law=self.name, message="class has no pure method", witness={"cls": cls}),))
		lhs = cls.pure(x).ap(cls.pure(f))
		rhs = cls.pure(f(x))
		ok = lhs == rhs
		violations: Sequence[Violation[Tuple[type, Callable[[A], B], A]]] = () if ok else (
			Violation(law=self.name, message="pure(x).ap(pure(f)) != pure(f(x))", witness={"x": x}),
		)
		return LawResult(self.name, ok, violations)


@dataclass(frozen=True)
class ApplicativeInterchangeLaw(Law[Tuple[ApplicativeT[A], Callable[[A], B], A]]):
	name: str = "applicative.interchange"
	tags: Sequence[str] = ("applicative",)

	def run(self, ctx: Tuple[ApplicativeT[A], Callable[[A], B], A], config: Dict[str, Any]) -> LawResult[Tuple[ApplicativeT[A], Callable[[A], B], A]]:
		v, f, x = ctx
		cls = type(v)
		if not hasattr(cls, "pure"):
			return LawResult(self.name, False, (Violation(law=self.name, message="class has no pure method", witness={"v": v}),))
		lhs: ApplicativeT[A] = cls.pure(x).ap(v.map(lambda g: g))
		rhs: ApplicativeT[A] = v.ap(cls.pure(lambda g: g(x)))
		ok = lhs == rhs
		violations: Sequence[Violation[Tuple[ApplicativeT[A], Callable[[A], B], A]]] = () if ok else (
			Violation(law=self.name, message="pure(x).ap(u.map(id)) != u.ap(pure(lambda g: g(x)))", witness={"x": x}),
		)
		return LawResult(self.name, ok, violations)


@dataclass(frozen=True)
class ApplicativeCompositionLaw(Law[Tuple[ApplicativeT[A], ApplicativeT[Callable[[A], B]], ApplicativeT[Callable[[B], C]]]]):
	name: str = "applicative.composition"
	tags: Sequence[str] = ("applicative",)

	def run(self, ctx: Tuple[ApplicativeT[A], ApplicativeT[Callable[[A], B]], ApplicativeT[Callable[[B], C]]], config: Dict[str, Any]) -> LawResult[Tuple[ApplicativeT[A], ApplicativeT[Callable[[A], B]], ApplicativeT[Callable[[B], C]]]]:
		v, u, w = ctx
		cls = type(v)
		if not hasattr(cls, "pure"):
			return LawResult(self.name, False, (Violation(law=self.name, message="class has no pure method", witness={"v": v}),))
		compose = lambda g: lambda f: lambda x: g(f(x))
		lhs: ApplicativeT[C] = v.ap(u.ap(w.map(compose)))
		rhs: ApplicativeT[C] = v.ap(u).ap(w)
		ok = lhs == rhs
		violations: Sequence[Violation[Tuple[ApplicativeT[A], ApplicativeT[Callable[[A], B]], ApplicativeT[Callable[[B], C]]]]] = () if ok else (
			Violation(law=self.name, message="composition law failed", witness={}),
		)
		return LawResult(self.name, ok, violations)


# -----------------------------
# Monad laws
# -----------------------------


@dataclass(frozen=True)
class MonadLeftIdentityLaw(Law[Tuple[type, Callable[[A], MonadT[B]], A]]):
	name: str = "monad.left_identity"
	tags: Sequence[str] = ("monad",)

	def run(self, ctx: Tuple[type, Callable[[A], MonadT[B]], A], config: Dict[str, Any]) -> LawResult[Tuple[type, Callable[[A], MonadT[B]], A]]:
		cls, f, a = ctx
		if not hasattr(cls, "pure"):
			return LawResult(self.name, False, (Violation(law=self.name, message="class has no pure method", witness={"cls": cls}),))
		lhs = cls.pure(a).bind(f)
		rhs = f(a)
		ok = lhs == rhs
		violations: Sequence[Violation[Tuple[type, Callable[[A], MonadT[B]], A]]] = () if ok else (
			Violation(law=self.name, message="pure(a).bind(f) != f(a)", witness={"a": a}),
		)
		return LawResult(self.name, ok, violations)


@dataclass(frozen=True)
class MonadRightIdentityLaw(Law[MonadT[A]]):
	name: str = "monad.right_identity"
	tags: Sequence[str] = ("monad",)

	def run(self, ctx: MonadT[A], config: Dict[str, Any]) -> LawResult[MonadT[A]]:
		cls = type(ctx)
		if not hasattr(cls, "pure"):
			return LawResult(self.name, False, (Violation(law=self.name, message="class has no pure method", witness={"ctx": ctx}),))
		ok = ctx.bind(lambda x: cls.pure(x)) == ctx
		violations: Sequence[Violation[MonadT[A]]] = () if ok else (
			Violation(law=self.name, message="m.bind(pure) != m", witness={"ctx": ctx}),
		)
		return LawResult(self.name, ok, violations)


@dataclass(frozen=True)
class MonadAssociativityLaw(Law[Tuple[MonadT[A], Callable[[A], MonadT[B]], Callable[[B], MonadT[C]]]]):
	name: str = "monad.associativity"
	tags: Sequence[str] = ("monad",)

	def run(self, ctx: Tuple[MonadT[A], Callable[[A], MonadT[B]], Callable[[B], MonadT[C]]], config: Dict[str, Any]) -> LawResult[Tuple[MonadT[A], Callable[[A], MonadT[B]], Callable[[B], MonadT[C]]]]:
		m, f, g = ctx
		lhs = m.bind(f).bind(g)
		rhs = m.bind(lambda x: f(x).bind(g))
		ok = lhs == rhs
		violations: Sequence[Violation[Tuple[MonadT[A], Callable[[A], MonadT[B]], Callable[[B], MonadT[C]]]]] = () if ok else (
			Violation(law=self.name, message="(m >>= f) >>= g != m >>= (\\x -> f x >>= g)", witness={"m": m}),
		)
		return LawResult(self.name, ok, violations)


# -----------------------------
# Law suites
# -----------------------------


@dataclass(frozen=True)
class LawSuite(Generic[A]):
	"""A collection of laws to run on a context."""

	name: str
	laws: Sequence[Law[A]]

	def run(self, ctx: A, config: Dict[str, Any]) -> Sequence[LawResult[A]]:
		"""Run all laws in this suite on the given context."""
		return [law.run(ctx, config) for law in self.laws]


@dataclass(frozen=True)
class FunctorLawSuite(LawSuite[FunctorT[A]]):
	"""Laws that every functor must satisfy."""

	name: str = "functor"
	laws: Sequence[Law[FunctorT[A]]] = (
		FunctorIdentityLaw[A](),
		FunctorCompositionLaw[A, A, A](),
	)


@dataclass(frozen=True)
class ApplicativeLawSuite(LawSuite[ApplicativeT[A]]):
	"""Laws that every applicative must satisfy."""

	name: str = "applicative"
	laws: Sequence[Law[ApplicativeT[A]]] = (
		ApplicativeIdentityLaw[A](),
		ApplicativeHomomorphismLaw[A, A](),
		ApplicativeInterchangeLaw[A, A](),
		ApplicativeCompositionLaw[A, A, A](),
	)


@dataclass(frozen=True)
class MonadLawSuite(LawSuite[MonadT[A]]):
	"""Laws that every monad must satisfy."""

	name: str = "monad"
	laws: Sequence[Law[MonadT[A]]] = (
		MonadLeftIdentityLaw[A, A](),
		MonadRightIdentityLaw[A](),
		MonadAssociativityLaw[A, A, A](),
	)


