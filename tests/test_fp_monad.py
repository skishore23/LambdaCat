from __future__ import annotations

from typing import Callable

import hypothesis.strategies as st
from hypothesis import given

from LambdaCat.core.fp.instances.identity import Id
from LambdaCat.core.fp.instances.maybe import Maybe
from LambdaCat.core.fp.instances.either import Either


def int_functions() -> list[Callable[[int], int]]:
	return [
		lambda x: x,
		lambda x: x + 1,
		lambda x: x - 1,
		lambda x: x * 2,
		lambda x: -x,
	]


@given(st.integers(), st.sampled_from(int_functions()))
def test_monad_left_identity_id(a: int, f: Callable[[int], int]) -> None:
	fm = lambda x: Id(f(x))
	assert Id.pure(a).bind(fm) == fm(a)


@given(st.one_of(st.integers(), st.none()), st.sampled_from(int_functions()))
def test_monad_left_identity_maybe(a: int | None, f: Callable[[int], int | None]) -> None:
	# Only test on non-None a to respect function domain for Maybe
	if a is None:
		return
	fm = lambda x: Maybe(f(x))
	assert Maybe.pure(a).bind(fm) == fm(a)


@given(st.integers())
def test_monad_right_identity_id(a: int) -> None:
	m = Id(a)
	assert m.bind(lambda x: Id.pure(x)) == m


@given(st.one_of(st.integers(), st.none()))
def test_monad_right_identity_maybe(a: int | None) -> None:
	m = Maybe(a)
	assert m.bind(lambda x: Maybe.pure(x)) == m


@given(st.integers(), st.sampled_from(int_functions()), st.sampled_from(int_functions()))
def test_monad_associativity_id(a: int, f: Callable[[int], int], g: Callable[[int], int]) -> None:
	m = Id(a)
	fm = lambda x: Id(f(x))
	gm = lambda y: Id(g(y))
	assert m.bind(fm).bind(gm) == m.bind(lambda x: fm(x).bind(gm))


@given(st.one_of(st.integers(), st.none()), st.sampled_from(int_functions()), st.sampled_from(int_functions()))
def test_monad_associativity_maybe(a: int | None, f: Callable[[int], int | None], g: Callable[[int], int | None]) -> None:
	m = Maybe(a)
	fm = lambda x: Maybe(f(x))
	gm = lambda y: Maybe(g(y))
	assert m.bind(fm).bind(gm) == m.bind(lambda x: fm(x).bind(gm))



@given(st.integers(), st.sampled_from(int_functions()))
def test_monad_left_identity_either_right(a: int, f: Callable[[int], int]) -> None:
	fm = lambda x: Either.right_value(f(x))
	assert Either.pure(a).bind(fm) == fm(a)


def test_monad_left_identity_either_left() -> None:
	fm = lambda x: Either.right_value(x)
	left: Either[str, int] = Either.left_value("err")
	assert left.bind(fm) == left


@given(st.integers())
def test_monad_right_identity_either_right(a: int) -> None:
	m = Either.right_value(a)
	assert m.bind(lambda x: Either.pure(x)) == m


def test_monad_right_identity_either_left() -> None:
	m: Either[str, int] = Either.left_value("err")
	assert m.bind(lambda x: Either.pure(x)) == m


@given(st.integers(), st.sampled_from(int_functions()), st.sampled_from(int_functions()))
def test_monad_associativity_either_right(a: int, f: Callable[[int], int], g: Callable[[int], int]) -> None:
	m = Either.right_value(a)
	fm = lambda x: Either.right_value(f(x))
	gm = lambda y: Either.right_value(g(y))
	assert m.bind(fm).bind(gm) == m.bind(lambda x: fm(x).bind(gm))


def test_monad_associativity_either_left() -> None:
	m: Either[str, int] = Either.left_value("err")
	fm = lambda x: Either.right_value(x + 1)
	gm = lambda y: Either.right_value(y * 2)
	assert m.bind(fm).bind(gm) == m.bind(lambda x: fm(x).bind(gm))

