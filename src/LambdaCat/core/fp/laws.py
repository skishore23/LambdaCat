from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Sequence, Tuple, TypeVar

from ..laws import Law, LawResult, LawSuite, Violation
from .typeclasses import ApplicativeT, FunctorT, MonadT


A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


# -----------------------------
# Functor laws
# -----------------------------


@dataclass(frozen=True)
class FunctorIdentityLaw(Law[FunctorT[A]]):
	name: str = "functor.identity"
	tags: Sequence[str] = ("functor",)

	def run(self, ctx: FunctorT[A], config: Dict[str, Any]) -> LawResult[FunctorT[A]]:
		mapped = ctx.map(lambda x: x)
		ok = mapped == ctx
		violations: Sequence[Violation[FunctorT[A]]] = () if ok else (
			Violation(law=self.name, message="map(id) != id", witness={"ctx": ctx}),
		)
		return LawResult(self.name, ok, violations)


@dataclass(frozen=True)
class FunctorCompositionLaw(Law[Tuple[FunctorT[A], Callable[[B], C], Callable[[A], B]]]):
	name: str = "functor.composition"
	tags: Sequence[str] = ("functor",)

	def run(self, ctx: Tuple[FunctorT[A], Callable[[B], C], Callable[[A], B]], config: Dict[str, Any]) -> LawResult[Tuple[FunctorT[A], Callable[[B], C], Callable[[A], B]]]:
		fa, g, f = ctx
		lhs = fa.map(lambda a: g(f(a)))
		rhs = fa.map(f).map(g)
		ok = lhs == rhs
		violations: Sequence[Violation[Tuple[FunctorT[A], Callable[[B], C], Callable[[A], B]]]] = () if ok else (
			Violation(law=self.name, message="map(g∘f) != map(g)∘map(f)", witness={"fa": fa}),
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
		lhs = cls.pure(x).ap(v.map(lambda g: g))
		rhs = v.ap(cls.pure(lambda g: g(x)))
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
		compose = lambda g: lambda f: lambda x: g(f(x))
		lhs = v.ap(u.ap(w.map(compose)))
		rhs = v.ap(u).ap(w)
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
			Violation(law=self.name, message="associativity failed", witness={}),
		)
		return LawResult(self.name, ok, violations)


# Suites
FUNCTOR_SUITE: LawSuite[FunctorT[Any]] = LawSuite(
	name="FUNCTOR_SUITE",
	laws=(FunctorIdentityLaw(),),
)

APPLICATIVE_SUITE: LawSuite[ApplicativeT[Any]] = LawSuite(
	name="APPLICATIVE_SUITE",
	laws=(ApplicativeIdentityLaw(),),
)

MONAD_SUITE: LawSuite[MonadT[Any]] = LawSuite(
	name="MONAD_SUITE",
	laws=(MonadRightIdentityLaw(),),
)


