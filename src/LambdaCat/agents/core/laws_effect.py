from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, TypeVar

import pytest
from hypothesis import given
from hypothesis import strategies as st

from .effect import Effect, Err, Ok, Result
from .patch import patch_combine

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
S = TypeVar("S")


# Test data generators
def state_strategy():
    """Generate test states."""
    return st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.one_of(
            st.text(),
            st.integers(),
            st.floats(),
            st.booleans(),
            st.lists(st.text())
        )
    )


def context_strategy():
    """Generate test contexts."""
    return st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.one_of(
            st.text(),
            st.integers(),
            st.floats(),
            st.booleans()
        )
    )


def function_strategy():
    """Generate test functions."""
    return st.functions(
        like=lambda x: x,
        returns=st.one_of(st.text(), st.integers(), st.floats())
    )


# Monad laws tests
class TestEffectMonadLaws:
    """Test Effect monad laws."""

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_left_identity(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test left identity: pure(a) >>= f = f(a)"""
        a = "test_value"
        f = lambda x: Effect.pure(f"processed_{x}")

        # pure(a) >>= f
        left_side = Effect.pure(a).bind(f)
        left_result = await left_side.run(state, ctx)

        # f(a)
        right_side = f(a)
        right_result = await right_side.run(state, ctx)

        assert left_result == right_result

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_right_identity(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test right identity: m >>= pure = m"""
        # Create a test effect
        m = Effect.pure("test_value")

        # m >>= pure
        left_side = m.bind(Effect.pure)
        left_result = await left_side.run(state, ctx)

        # m
        right_result = await m.run(state, ctx)

        assert left_result == right_result

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_associativity(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test associativity: (m >>= f) >>= g = m >>= (λx. f(x) >>= g)"""
        m = Effect.pure("test_value")
        f = lambda x: Effect.pure(f"f_{x}")
        g = lambda x: Effect.pure(f"g_{x}")

        # (m >>= f) >>= g
        left_side = m.bind(f).bind(g)
        left_result = await left_side.run(state, ctx)

        # m >>= (λx. f(x) >>= g)
        right_side = m.bind(lambda x: f(x).bind(g))
        right_result = await right_side.run(state, ctx)

        assert left_result == right_result


# Functor laws tests
class TestEffectFunctorLaws:
    """Test Effect functor laws."""

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_identity(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test identity: fmap id = id"""
        m = Effect.pure("test_value")

        # fmap id
        left_side = m.map(lambda x: x)
        left_result = await left_side.run(state, ctx)

        # id
        right_result = await m.run(state, ctx)

        assert left_result == right_result

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_composition(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test composition: fmap (f . g) = fmap f . fmap g"""
        m = Effect.pure("test_value")
        f = lambda x: f"f_{x}"
        g = lambda x: f"g_{x}"

        # fmap (f . g)
        left_side = m.map(lambda x: f(g(x)))
        left_result = await left_side.run(state, ctx)

        # fmap f . fmap g
        right_side = m.map(g).map(f)
        right_result = await right_side.run(state, ctx)

        assert left_result == right_result


# Applicative laws tests
class TestEffectApplicativeLaws:
    """Test Effect applicative laws."""

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_identity(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test identity: pure id <*> v = v"""
        v = Effect.pure("test_value")

        # pure id <*> v
        left_side = Effect.pure(lambda x: x).ap(v)
        left_result = await left_side.run(state, ctx)

        # v
        right_result = await v.run(state, ctx)

        assert left_result == right_result

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_homomorphism(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test homomorphism: pure f <*> pure x = pure (f x)"""
        f = lambda x: f"processed_{x}"
        x = "test_value"

        # pure f <*> pure x
        left_side = Effect.pure(f).ap(Effect.pure(x))
        left_result = await left_side.run(state, ctx)

        # pure (f x)
        right_side = Effect.pure(f(x))
        right_result = await right_side.run(state, ctx)

        assert left_result == right_result

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_interchange(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test interchange: u <*> pure y = pure ($ y) <*> u"""
        u = Effect.pure(lambda x: f"processed_{x}")
        y = "test_value"

        # u <*> pure y
        left_side = u.ap(Effect.pure(y))
        left_result = await left_side.run(state, ctx)

        # pure ($ y) <*> u
        right_side = Effect.pure(lambda f: f(y)).ap(u)
        right_result = await right_side.run(state, ctx)

        assert left_result == right_result

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_composition(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test composition: pure (.) <*> u <*> v <*> w = u <*> (v <*> w)"""
        u = Effect.pure(lambda x: f"u_{x}")
        v = Effect.pure(lambda x: f"v_{x}")
        w = Effect.pure("test_value")

        # pure (.) <*> u <*> v <*> w
        compose = lambda f: lambda g: lambda x: f(g(x))
        left_side = Effect.pure(compose).ap(u).ap(v).ap(w)
        left_result = await left_side.run(state, ctx)

        # u <*> (v <*> w)
        right_side = u.ap(v.ap(w))
        right_result = await right_side.run(state, ctx)

        assert left_result == right_result


# Parallel composition tests
class TestEffectParallelComposition:
    """Test parallel composition properties."""

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_parallel_identity(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test parallel composition with single effect."""
        effect = Effect.pure("test_value")

        result = await Effect.par_mapN(patch_combine, effect).run(state, ctx)

        # Should return the single effect's result
        assert result[2].value == ("test_value",)

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_parallel_empty(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test parallel composition with no effects."""
        result = await Effect.par_mapN(patch_combine).run(state, ctx)

        # Should return empty tuple
        assert result[2].value == ()

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_parallel_error_propagation(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test that errors in parallel composition are propagated."""
        error_effect = Effect(lambda s, ctx: (s, [], Err("test_error")))
        success_effect = Effect.pure("success")

        result = await Effect.par_mapN(patch_combine, error_effect, success_effect).run(state, ctx)

        # Should return error
        assert isinstance(result[2], Err)
        assert result[2].error == "test_error"

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_parallel_state_merging(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test that parallel effects merge state correctly."""
        def create_effect(key: str, value: str) -> Effect[Dict[str, Any], str]:
            async def effect_fn(s: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Result[str]]:
                new_state = dict(s)
                new_state[key] = value
                return (new_state, [], Ok(value))
            return Effect(effect_fn)

        effect1 = create_effect("key1", "value1")
        effect2 = create_effect("key2", "value2")

        result = await Effect.par_mapN(patch_combine, effect1, effect2).run(state, ctx)

        # Check that both keys are in the final state
        final_state = result[0]
        assert final_state["key1"] == "value1"
        assert final_state["key2"] == "value2"
        assert result[2].value == ("value1", "value2")


# Race/Alt laws tests
class TestEffectRaceLaws:
    """Test Effect race/Alt laws."""

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_race_identity(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test race with single effect."""
        effect = Effect.pure("test_value")

        result = await Effect.race_first(effect).run(state, ctx)

        # Should return the single effect's result
        assert result[2].value == "test_value"

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_race_empty(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test race with no effects."""
        with pytest.raises(ValueError):
            await Effect.race_first().run(state, ctx)

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_race_first_success(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test that race returns first successful result."""
        # Create effects with different delays
        async def slow_effect(s: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Result[str]]:
            await asyncio.sleep(0.1)
            return (s, [], Ok("slow"))

        async def fast_effect(s: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Result[str]]:
            await asyncio.sleep(0.01)
            return (s, [], Ok("fast"))

        slow = Effect(slow_effect)
        fast = Effect(fast_effect)

        result = await Effect.race_first(fast, slow).run(state, ctx)

        # Should return the fast result
        assert result[2].value == "fast"


# Timeout tests
class TestEffectTimeout:
    """Test Effect timeout functionality."""

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_timeout_success(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test timeout with successful effect."""
        effect = Effect.pure("success")
        timeout_effect = Effect.timeout(1.0, effect)

        result = await timeout_effect.run(state, ctx)

        assert result[2].value == "success"

    @pytest.mark.asyncio
    @given(state_strategy(), context_strategy())
    async def test_timeout_failure(self, state: Dict[str, Any], ctx: Dict[str, Any]):
        """Test timeout with slow effect."""
        async def slow_effect(s: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Result[str]]:
            await asyncio.sleep(0.1)
            return (s, [], Ok("slow"))

        effect = Effect(slow_effect)
        timeout_effect = Effect.timeout(0.01, effect)

        result = await timeout_effect.run(state, ctx)

        # Should timeout
        assert isinstance(result[2], Err)
        assert result[2].error == "timeout"


# Integration tests
class TestEffectIntegration:
    """Test Effect integration scenarios."""

    @pytest.mark.asyncio
    async def test_complex_workflow(self):
        """Test a complex workflow with multiple effects."""
        state = {"step": 0, "data": []}
        ctx = {}

        # Create a sequence of effects
        def step_effect(step_name: str) -> Effect[Dict[str, Any], str]:
            async def effect_fn(s: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Result[str]]:
                new_state = dict(s)
                new_state["step"] += 1
                new_state["data"].append(step_name)
                return (new_state, [{"span": step_name}], Ok(step_name))
            return Effect(effect_fn)

        # Compose effects
        workflow = (
            step_effect("step1")
            .bind(lambda _: step_effect("step2"))
            .bind(lambda _: step_effect("step3"))
        )

        result = await workflow.run(state, ctx)

        # Check final state
        final_state = result[0]
        assert final_state["step"] == 3
        assert final_state["data"] == ["step1", "step2", "step3"]

        # Check trace
        trace = result[1]
        assert len(trace) == 3
        assert all(span["span"] in ["step1", "step2", "step3"] for span in trace)

        # Check result
        assert result[2].value == "step3"

    @pytest.mark.asyncio
    async def test_parallel_workflow(self):
        """Test parallel workflow with state merging."""
        state = {"results": []}
        ctx = {}

        def parallel_effect(name: str) -> Effect[Dict[str, Any], str]:
            async def effect_fn(s: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Result[str]]:
                new_state = dict(s)
                new_state["results"].append(name)
                return (new_state, [{"span": name}], Ok(name))
            return Effect(effect_fn)

        # Create parallel effects
        effects = [parallel_effect(f"task{i}") for i in range(3)]

        result = await Effect.par_mapN(patch_combine, *effects).run(state, ctx)

        # Check final state
        final_state = result[0]
        assert len(final_state["results"]) == 3
        assert set(final_state["results"]) == {"task0", "task1", "task2"}

        # Check result
        assert result[2].value == ("task0", "task1", "task2")


# Property-based tests
class TestEffectProperties:
    """Property-based tests for Effect."""

    @pytest.mark.asyncio
    @given(
        st.text(min_size=1, max_size=10),
        st.text(min_size=1, max_size=10),
        state_strategy(),
        context_strategy()
    )
    async def test_effect_pure_properties(
        self,
        value1: str,
        value2: str,
        state: Dict[str, Any],
        ctx: Dict[str, Any]
    ):
        """Test properties of pure effects."""
        effect1 = Effect.pure(value1)
        effect2 = Effect.pure(value2)

        # Pure effects should not modify state
        result1 = await effect1.run(state, ctx)
        result2 = await effect2.run(state, ctx)

        assert result1[0] == state  # State unchanged
        assert result2[0] == state  # State unchanged
        assert result1[2].value == value1
        assert result2[2].value == value2

    @pytest.mark.asyncio
    @given(
        st.text(min_size=1, max_size=10),
        st.functions(like=lambda x: f"processed_{x}", returns=st.text()),
        state_strategy(),
        context_strategy()
    )
    async def test_effect_map_properties(
        self,
        value: str,
        f: Callable[[str], str],
        state: Dict[str, Any],
        ctx: Dict[str, Any]
    ):
        """Test properties of effect mapping."""
        effect = Effect.pure(value)
        mapped = effect.map(f)

        result = await mapped.run(state, ctx)

        assert result[0] == state  # State unchanged
        assert result[2].value == f(value)

    @pytest.mark.asyncio
    @given(
        st.text(min_size=1, max_size=10),
        st.functions(like=lambda x: Effect.pure(f"bound_{x}"), returns=st.none()),
        state_strategy(),
        context_strategy()
    )
    async def test_effect_bind_properties(
        self,
        value: str,
        f: Callable[[str], Effect[Dict[str, Any], str]],
        state: Dict[str, Any],
        ctx: Dict[str, Any]
    ):
        """Test properties of effect binding."""
        effect = Effect.pure(value)
        bound = effect.bind(f)

        result = await bound.run(state, ctx)

        assert result[0] == state  # State unchanged
        assert result[2].value == f"bound_{value}"
