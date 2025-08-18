from __future__ import annotations

from typing import Callable

import hypothesis.strategies as st
from hypothesis import given

from LambdaCat.core.fp.instances.identity import Id
from LambdaCat.core.fp.instances.maybe import Maybe


def int_functions() -> list[Callable[[int], int]]:
	return [
		lambda x: x,
		lambda x: x + 1,
		lambda x: x - 1,
		lambda x: x * 2,
		lambda x: -x,
	]


@given(st.integers())
def test_applicative_identity_id(x: int) -> None:
	fx = Id(x)
	assert fx.ap(Id.pure(lambda a: a)) == fx


@given(st.one_of(st.integers(), st.none()))
def test_applicative_identity_maybe(x: int | None) -> None:
	fx = Maybe(x)
	assert fx.ap(Maybe.pure(lambda a: a)) == fx


@given(st.integers(), st.sampled_from(int_functions()))
def test_applicative_homomorphism_id(x: int, f: Callable[[int], int]) -> None:
	assert Id.pure(x).ap(Id.pure(f)) == Id.pure(f(x))


@given(st.integers(), st.sampled_from(int_functions()))
def test_applicative_homomorphism_maybe(x: int, f: Callable[[int], int]) -> None:
	assert Maybe.pure(x).ap(Maybe.pure(f)) == Maybe.pure(f(x))


