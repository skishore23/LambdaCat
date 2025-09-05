from __future__ import annotations

from typing import Callable

import hypothesis.strategies as st
from hypothesis import given

from src.LambdaCat.core.fp.instances.either import Either
from src.LambdaCat.core.fp.instances.identity import Id
from src.LambdaCat.core.fp.instances.maybe import Maybe


def int_functions() -> list[Callable[[int], int]]:
	return [
		lambda x: x,
		lambda x: x + 1,
		lambda x: x - 1,
		lambda x: x * 2,
		lambda x: -x,
	]


@given(st.integers())
def test_functor_identity_id(x: int) -> None:
	fx = Id(x)
	assert fx.map(lambda a: a) == fx


@given(st.integers())
def test_functor_identity_maybe(x: int) -> None:
	fx = Maybe(x)
	assert fx.map(lambda a: a) == fx
	assert Maybe(None).map(lambda a: a) == Maybe(None)


@given(st.integers(), st.sampled_from(int_functions()), st.sampled_from(int_functions()))
def test_functor_composition_id(x: int, g: Callable[[int], int], f: Callable[[int], int]) -> None:
	fx = Id(x)
	lhs = fx.map(lambda a: g(f(a)))
	rhs = fx.map(f).map(g)
	assert lhs == rhs


@given(st.one_of(st.integers(), st.none()), st.sampled_from(int_functions()), st.sampled_from(int_functions()))
def test_functor_composition_maybe(x: int | None, g: Callable[[int], int], f: Callable[[int], int]) -> None:
	fx = Maybe(x)
	lhs = fx.map(lambda a: g(f(a)))
	rhs = fx.map(f).map(g)
	assert lhs == rhs



@given(st.integers())
def test_functor_identity_either_right(x: int) -> None:
	fx: Either[str, int] = Either.right_value(x)
	assert fx.map(lambda a: a) == fx


def test_functor_identity_either_left() -> None:
	fx: Either[str, int] = Either.left_value("err")
	assert fx.map(lambda a: a) == fx


@given(st.integers(), st.sampled_from(int_functions()), st.sampled_from(int_functions()))
def test_functor_composition_either_right(x: int, g: Callable[[int], int], f: Callable[[int], int]) -> None:
	fx: Either[str, int] = Either.right_value(x)
	lhs = fx.map(lambda a: g(f(a)))
	rhs = fx.map(f).map(g)
	assert lhs == rhs


def test_functor_composition_either_left() -> None:
	fx: Either[str, int] = Either.left_value("err")
	def g(x):
		return x + 1
	def f(x):
		return x * 2
	lhs = fx.map(lambda a: g(f(a)))
	rhs = fx.map(f).map(g)
	assert lhs == rhs

