from __future__ import annotations

from typing import Callable, Generic, TypeVar

import hypothesis.strategies as st
from hypothesis import given

from LambdaCat.core.fp.instances.reader import Reader
from LambdaCat.core.fp.instances.writer import Writer
from LambdaCat.core.fp.instances.state import State
from LambdaCat.core.fp.typeclasses import Monoid


A = TypeVar("A")
R = TypeVar("R")
W = TypeVar("W")
S = TypeVar("S")


def int_functions() -> list[Callable[[int], int]]:
	return [
		lambda x: x,
		lambda x: x + 1,
		lambda x: x - 1,
		lambda x: x * 2,
		lambda x: -x,
	]


# -----------------
# Reader laws (test by evaluation, not instance equality)
# -----------------


@given(st.integers(), st.integers())
def test_reader_functor_identity(x: int, env: int) -> None:
	f = Reader(lambda _r: x)
	assert f.map(lambda a: a).run(env) == f.run(env)


@given(st.integers(), st.sampled_from(int_functions()), st.sampled_from(int_functions()), st.integers())
def test_reader_functor_composition(x: int, g: Callable[[int], int], f: Callable[[int], int], env: int) -> None:
	fa = Reader(lambda _r: x)
	lhs = fa.map(lambda a: g(f(a))).run(env)
	rhs = fa.map(f).map(g).run(env)
	assert lhs == rhs


@given(st.integers(), st.sampled_from(int_functions()), st.integers())
def test_reader_applicative_identity(x: int, f_id: Callable[[int], int], env: int) -> None:
	# f_id is unused; enforce shape only
	v = Reader(lambda _r: x)
	assert v.ap(Reader(lambda _r: (lambda a: a))).run(env) == v.run(env)


@given(st.integers(), st.sampled_from(int_functions()), st.integers())
def test_reader_monad_right_identity(x: int, f_id: Callable[[int], int], env: int) -> None:
	m = Reader(lambda _r: x)
	assert m.bind(lambda a: Reader.pure(a)).run(env) == m.run(env)


@given(st.integers(), st.sampled_from(int_functions()), st.sampled_from(int_functions()), st.integers())
def test_reader_monad_associativity(x: int, f: Callable[[int], int], g: Callable[[int], int], env: int) -> None:
	m = Reader(lambda _r: x)
	fm = lambda a: Reader(lambda _r: f(a))
	gm = lambda b: Reader(lambda _r: g(b))
	left = m.bind(fm).bind(gm).run(env)
	right = m.bind(lambda a: fm(a).bind(gm)).run(env)
	assert left == right


# -----------------
# Writer laws (requires a Monoid instance; compare by instance equality)
# -----------------


class ListMonoid(Monoid[list[int]]):
	def empty(self) -> list[int]:
		return []

	def combine(self, left: list[int], right: list[int]) -> list[int]:
		return left + right


@given(st.integers())
def test_writer_applicative_identity(x: int) -> None:
	W = ListMonoid()
	v = Writer.pure(x, W)
	assert v.ap(Writer.pure(lambda a: a, W)) == v


@given(st.integers(), st.sampled_from(int_functions()))
def test_writer_applicative_homomorphism(x: int, f: Callable[[int], int]) -> None:
	W = ListMonoid()
	assert Writer.pure(x, W).ap(Writer.pure(f, W)) == Writer.pure(f(x), W)


@given(st.integers())
def test_writer_monad_right_identity(x: int) -> None:
	W = ListMonoid()
	m = Writer.pure(x, W)
	assert m.bind(lambda a: Writer.pure(a, W)) == m


# -----------------
# State laws (test by evaluation of run(s))
# -----------------


@given(st.integers(), st.integers())
def test_state_functor_identity(x: int, s0: int) -> None:
	m = State(lambda s: (x, s))
	assert m.map(lambda a: a).run(s0) == m.run(s0)


@given(st.integers(), st.integers())
def test_state_applicative_identity(x: int, s0: int) -> None:
	v = State(lambda s: (x, s))
	id_state = State(lambda s: (lambda a: a, s))
	assert v.ap(id_state).run(s0) == v.run(s0)


@given(st.integers(), st.integers())
def test_state_monad_right_identity(x: int, s0: int) -> None:
	m = State(lambda s: (x, s))
	assert m.bind(lambda a: State.pure(a)).run(s0) == m.run(s0)


@given(st.integers(), st.sampled_from(int_functions()), st.sampled_from(int_functions()), st.integers())
def test_state_monad_associativity(x: int, f: Callable[[int], int], g: Callable[[int], int], s0: int) -> None:
	m = State(lambda s: (x, s))
	fm = lambda a: State(lambda s: (f(a), s))
	gm = lambda b: State(lambda s: (g(b), s))
	left = m.bind(fm).bind(gm).run(s0)
	right = m.bind(lambda a: fm(a).bind(gm)).run(s0)
	assert left == right


