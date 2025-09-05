#!/usr/bin/env python3
"""
Async Agent System Benchmarks

This module provides comprehensive benchmarks for the async agent system,
measuring performance, scalability, and correctness.
"""

import asyncio
import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from LambdaCat.agents.actions import choose, parallel, sequence, task
from LambdaCat.agents.cognition.memory import AgentState
from LambdaCat.agents.core.async_runtime import run_plan_async
from LambdaCat.agents.core.effect import Effect
from LambdaCat.agents.core.instruments import get_observability
from LambdaCat.agents.core.patch import patch_combine
from LambdaCat.agents.tools.http import create_http_adapter
from LambdaCat.agents.tools.llm import create_mock_llm
from LambdaCat.agents.tools.search import create_mock_search_adapter


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    duration_ms: float
    success: bool
    error: str = None
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata or {}
        }


class AsyncAgentBenchmarks:
    """Comprehensive benchmark suite for async agent system."""

    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: list[BenchmarkResult] = []
        self.obs = get_observability()

    async def run_all_benchmarks(self) -> list[BenchmarkResult]:
        """Run all benchmarks."""
        print("🚀 Starting Async Agent Benchmarks")
        print("=" * 50)

        # Core Effect benchmarks
        await self._benchmark_effect_creation()
        await self._benchmark_effect_composition()
        await self._benchmark_effect_parallel()

        # Runtime benchmarks
        await self._benchmark_sequential_plans()
        await self._benchmark_parallel_plans()
        await self._benchmark_choose_plans()

        # Tool adapter benchmarks
        await self._benchmark_llm_adapter()
        await self._benchmark_http_adapter()
        await self._benchmark_search_adapter()

        # Memory and beliefs benchmarks
        await self._benchmark_memory_operations()
        await self._benchmark_belief_updates()

        # Scalability benchmarks
        await self._benchmark_scalability()
        await self._benchmark_concurrent_agents()

        # Error handling benchmarks
        await self._benchmark_error_handling()

        # Save results
        await self._save_results()

        print(f"✅ Completed {len(self.results)} benchmarks")
        return self.results

    async def _benchmark_effect_creation(self):
        """Benchmark Effect creation and basic operations."""
        print("📊 Benchmarking Effect creation...")

        # Effect creation
        start_time = time.perf_counter()
        effects = [Effect.pure(f"value_{i}") for i in range(1000)]
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="effect_creation_1000",
            duration_ms=duration_ms,
            success=True,
            metadata={"count": 1000, "avg_per_effect": duration_ms / 1000}
        ))

        # Effect mapping
        start_time = time.perf_counter()
        [effect.map(lambda x: x.upper()) for effect in effects[:100]]
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="effect_mapping_100",
            duration_ms=duration_ms,
            success=True,
            metadata={"count": 100, "avg_per_effect": duration_ms / 100}
        ))

    async def _benchmark_effect_composition(self):
        """Benchmark Effect composition (bind)."""
        print("📊 Benchmarking Effect composition...")

        def create_effect_chain(length: int) -> Effect[dict[str, Any], str]:
            """Create a chain of effects."""
            effect = Effect.pure("start")
            for i in range(length):
                effect = effect.bind(lambda x, i=i: Effect.pure(f"{x}_{i}"))
            return effect

        # Test different chain lengths
        for length in [10, 50, 100, 200]:
            start_time = time.perf_counter()
            effect = create_effect_chain(length)
            # Run the effect
            state = {"data": "test"}
            ctx = {}
            await effect.run(state, ctx)
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.results.append(BenchmarkResult(
                name=f"effect_chain_{length}",
                duration_ms=duration_ms,
                success=True,
                metadata={"chain_length": length, "avg_per_bind": duration_ms / length}
            ))

    async def _benchmark_effect_parallel(self):
        """Benchmark parallel Effect composition."""
        print("📊 Benchmarking parallel Effects...")

        async def create_parallel_effect(count: int) -> Effect[dict[str, Any], tuple[str, ...]]:
            """Create parallel effects."""
            effects = [Effect.pure(f"value_{i}") for i in range(count)]
            return Effect.par_mapN(patch_combine, *effects)

        # Test different parallel counts
        for count in [2, 5, 10, 20, 50]:
            start_time = time.perf_counter()
            effect = create_parallel_effect(count)
            state = {"data": "test"}
            ctx = {}
            await effect.run(state, ctx)
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.results.append(BenchmarkResult(
                name=f"effect_parallel_{count}",
                duration_ms=duration_ms,
                success=True,
                metadata={"parallel_count": count, "avg_per_effect": duration_ms / count}
            ))

    async def _benchmark_sequential_plans(self):
        """Benchmark sequential plan execution."""
        print("📊 Benchmarking sequential plans...")

        async def create_action(name: str, delay: float = 0.001):
            """Create a test action."""
            async def action(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
                await asyncio.sleep(delay)
                return {**state, name: True}
            return action

        # Create action registry
        actions = {}
        for i in range(20):
            actions[f"action_{i}"] = await create_action(f"action_{i}")

        # Test different plan lengths
        for length in [5, 10, 15, 20]:
            plan = sequence(*[task(f"action_{i}") for i in range(length)])

            start_time = time.perf_counter()
            state = {"data": "test"}
            ctx = {}
            await run_plan_async(plan, actions, state, ctx)
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.results.append(BenchmarkResult(
                name=f"sequential_plan_{length}",
                duration_ms=duration_ms,
                success=True,
                metadata={"plan_length": length, "avg_per_action": duration_ms / length}
            ))

    async def _benchmark_parallel_plans(self):
        """Benchmark parallel plan execution."""
        print("📊 Benchmarking parallel plans...")

        async def create_action(name: str, delay: float = 0.01):
            """Create a test action."""
            async def action(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
                await asyncio.sleep(delay)
                return {**state, name: True}
            return action

        # Create action registry
        actions = {}
        for i in range(20):
            actions[f"action_{i}"] = await create_action(f"action_{i}")

        # Test different parallel counts
        for count in [2, 5, 10, 15, 20]:
            plan = parallel(*[task(f"action_{i}") for i in range(count)])

            start_time = time.perf_counter()
            state = {"data": "test"}
            ctx = {}
            await run_plan_async(plan, actions, state, ctx)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Calculate speedup vs sequential
            sequential_time = count * 0.01 * 1000  # Expected sequential time
            speedup = sequential_time / duration_ms if duration_ms > 0 else 0

            self.results.append(BenchmarkResult(
                name=f"parallel_plan_{count}",
                duration_ms=duration_ms,
                success=True,
                metadata={
                    "parallel_count": count,
                    "speedup": speedup,
                    "expected_sequential_ms": sequential_time
                }
            ))

    async def _benchmark_choose_plans(self):
        """Benchmark choose plan execution."""
        print("📊 Benchmarking choose plans...")

        async def create_action(name: str, delay: float = 0.01):
            """Create a test action."""
            async def action(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
                await asyncio.sleep(delay)
                return {**state, name: True}
            return action

        # Create action registry
        actions = {}
        for i in range(10):
            actions[f"action_{i}"] = await create_action(f"action_{i}")

        # Test different choice counts
        for count in [2, 5, 10]:
            plan = choose(*[task(f"action_{i}") for i in range(count)])

            start_time = time.perf_counter()
            state = {"data": "test"}
            ctx = {}
            await run_plan_async(plan, actions, state, ctx)
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.results.append(BenchmarkResult(
                name=f"choose_plan_{count}",
                duration_ms=duration_ms,
                success=True,
                metadata={"choice_count": count}
            ))

    async def _benchmark_llm_adapter(self):
        """Benchmark LLM adapter performance."""
        print("📊 Benchmarking LLM adapter...")

        # Create mock LLM
        llm = create_mock_llm(responses=[f"Response {i}" for i in range(100)])

        # Test single completion
        start_time = time.perf_counter()
        response = await llm.complete("Test prompt")
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="llm_single_completion",
            duration_ms=duration_ms,
            success=True,
            metadata={"response_length": len(response.content)}
        ))

        # Test batch completions
        start_time = time.perf_counter()
        tasks = [llm.complete(f"Prompt {i}") for i in range(10)]
        await asyncio.gather(*tasks)
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="llm_batch_10",
            duration_ms=duration_ms,
            success=True,
            metadata={"batch_size": 10, "avg_per_completion": duration_ms / 10}
        ))

    async def _benchmark_http_adapter(self):
        """Benchmark HTTP adapter performance."""
        print("📊 Benchmarking HTTP adapter...")

        # Create HTTP adapter
        http = create_http_adapter()

        # Test single request (will fail with mock, but we can measure setup time)
        start_time = time.perf_counter()
        try:
            await http.get("https://httpbin.org/delay/0.1")
        except Exception:
            pass  # Expected to fail in test environment
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="http_single_request",
            duration_ms=duration_ms,
            success=False,  # Expected to fail
            error="Mock HTTP request failed"
        ))

        await http.close()

    async def _benchmark_search_adapter(self):
        """Benchmark search adapter performance."""
        print("📊 Benchmarking search adapter...")

        # Create mock search adapter
        search = create_mock_search_adapter()

        # Test single search
        start_time = time.perf_counter()
        results = await search.search("test query", num_results=10)
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="search_single_query",
            duration_ms=duration_ms,
            success=True,
            metadata={"result_count": len(results)}
        ))

        # Test multiple searches
        start_time = time.perf_counter()
        tasks = [search.search(f"query {i}") for i in range(5)]
        await asyncio.gather(*tasks)
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="search_batch_5",
            duration_ms=duration_ms,
            success=True,
            metadata={"batch_size": 5, "avg_per_query": duration_ms / 5}
        ))

    async def _benchmark_memory_operations(self):
        """Benchmark memory operations."""
        print("📊 Benchmarking memory operations...")

        # Test AgentState creation
        start_time = time.perf_counter()
        [AgentState() for _ in range(1000)]
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="memory_agent_state_creation_1000",
            duration_ms=duration_ms,
            success=True,
            metadata={"count": 1000, "avg_per_state": duration_ms / 1000}
        ))

        # Test memory operations
        state = AgentState()
        start_time = time.perf_counter()
        for i in range(1000):
            state = state.remember(f"key_{i}", f"value_{i}")
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="memory_remember_1000",
            duration_ms=duration_ms,
            success=True,
            metadata={"count": 1000, "avg_per_operation": duration_ms / 1000}
        ))

        # Test belief updates
        from LambdaCat.agents.cognition.beliefs import create_belief_system
        belief_system = create_belief_system()

        start_time = time.perf_counter()
        for i in range(1000):
            belief_system = belief_system.add_belief(f"proposition_{i}", 0.5)
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="memory_belief_add_1000",
            duration_ms=duration_ms,
            success=True,
            metadata={"count": 1000, "avg_per_belief": duration_ms / 1000}
        ))

    async def _benchmark_belief_updates(self):
        """Benchmark belief update operations."""
        print("📊 Benchmarking belief updates...")

        from LambdaCat.agents.cognition.beliefs import create_belief_system

        belief_system = create_belief_system()

        # Add initial beliefs
        for i in range(100):
            belief_system = belief_system.add_belief(f"prop_{i}", 0.0)

        # Test belief updates
        start_time = time.perf_counter()
        for i in range(1000):
            belief_system = belief_system.update_belief(f"prop_{i % 100}", 0.1)
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="belief_update_1000",
            duration_ms=duration_ms,
            success=True,
            metadata={"count": 1000, "avg_per_update": duration_ms / 1000}
        ))

        # Test belief decay
        start_time = time.perf_counter()
        belief_system = belief_system.decay_all_beliefs()
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="belief_decay_100",
            duration_ms=duration_ms,
            success=True,
            metadata={"belief_count": 100}
        ))

    async def _benchmark_scalability(self):
        """Benchmark system scalability."""
        print("📊 Benchmarking scalability...")

        async def create_scalable_plan(parallel_count: int, sequential_depth: int):
            """Create a scalable plan."""
            # Create actions
            actions = {}
            for i in range(parallel_count * sequential_depth):
                async def action(state: dict[str, Any], ctx: dict[str, Any], idx: int = i) -> dict[str, Any]:
                    await asyncio.sleep(0.001)  # Small delay
                    return {**state, f"action_{idx}": True}
                actions[f"action_{i}"] = action

            # Create plan with parallel branches, each with sequential depth
            branches = []
            for branch in range(parallel_count):
                branch_actions = [task(f"action_{branch * sequential_depth + i}") for i in range(sequential_depth)]
                branches.append(sequence(*branch_actions))

            return parallel(*branches), actions

        # Test different scales
        for parallel_count in [2, 5, 10]:
            for sequential_depth in [2, 5]:
                plan, actions = await create_scalable_plan(parallel_count, sequential_depth)

                start_time = time.perf_counter()
                state = {"data": "test"}
                ctx = {}
                await run_plan_async(plan, actions, state, ctx)
                duration_ms = (time.perf_counter() - start_time) * 1000

                self.results.append(BenchmarkResult(
                    name=f"scalability_p{parallel_count}_s{sequential_depth}",
                    duration_ms=duration_ms,
                    success=True,
                    metadata={
                        "parallel_count": parallel_count,
                        "sequential_depth": sequential_depth,
                        "total_actions": parallel_count * sequential_depth
                    }
                ))

    async def _benchmark_concurrent_agents(self):
        """Benchmark concurrent agent execution."""
        print("📊 Benchmarking concurrent agents...")

        async def create_agent(agent_id: str, work_duration: float = 0.01):
            """Create a test agent."""
            async def agent_work():
                await asyncio.sleep(work_duration)
                return f"agent_{agent_id}_completed"

            return agent_work

        # Test different agent counts
        for agent_count in [2, 5, 10, 20]:
            start_time = time.perf_counter()
            agents = [create_agent(f"agent_{i}") for i in range(agent_count)]
            results = await asyncio.gather(*[agent() for agent in agents])
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.results.append(BenchmarkResult(
                name=f"concurrent_agents_{agent_count}",
                duration_ms=duration_ms,
                success=True,
                metadata={
                    "agent_count": agent_count,
                    "avg_per_agent": duration_ms / agent_count,
                    "results_count": len(results)
                }
            ))

    async def _benchmark_error_handling(self):
        """Benchmark error handling performance."""
        print("📊 Benchmarking error handling...")

        async def failing_action(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
            """Action that always fails."""
            raise Exception("Simulated failure")

        async def succeeding_action(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
            """Action that always succeeds."""
            return {**state, "success": True}

        # Test error handling in sequential plans
        actions = {
            "failing": failing_action,
            "succeeding": succeeding_action
        }

        plan = sequence(task("failing"), task("succeeding"))

        start_time = time.perf_counter()
        try:
            state = {"data": "test"}
            ctx = {}
            await run_plan_async(plan, actions, state, ctx)
        except Exception:
            pass  # Expected to fail
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="error_handling_sequential",
            duration_ms=duration_ms,
            success=False,
            error="Expected failure in sequential plan"
        ))

        # Test error handling in parallel plans
        plan = parallel(task("failing"), task("succeeding"))

        start_time = time.perf_counter()
        try:
            state = {"data": "test"}
            ctx = {}
            await run_plan_async(plan, actions, state, ctx)
        except Exception:
            pass  # Expected to fail
        duration_ms = (time.perf_counter() - start_time) * 1000

        self.results.append(BenchmarkResult(
            name="error_handling_parallel",
            duration_ms=duration_ms,
            success=False,
            error="Expected failure in parallel plan"
        ))

    async def _save_results(self):
        """Save benchmark results to files."""
        # Save JSON results
        json_file = self.output_dir / "benchmark_results.json"
        with open(json_file, "w") as f:
            json.dump([result.to_dict() for result in self.results], f, indent=2)

        # Save CSV results
        csv_file = self.output_dir / "benchmark_results.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "duration_ms", "success", "error", "metadata"])
            writer.writeheader()
            for result in self.results:
                row = result.to_dict()
                # Flatten metadata
                if row["metadata"]:
                    for key, value in row["metadata"].items():
                        row[f"meta_{key}"] = value
                    del row["metadata"]
                writer.writerow(row)

        # Generate summary report
        await self._generate_summary_report()

        print(f"📁 Results saved to {self.output_dir}")

    async def _generate_summary_report(self):
        """Generate a summary report."""
        report_file = self.output_dir / "benchmark_summary.md"

        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]

        with open(report_file, "w") as f:
            f.write("# Async Agent System Benchmark Results\n\n")
            f.write(f"**Total Benchmarks:** {len(self.results)}\n")
            f.write(f"**Successful:** {len(successful_results)}\n")
            f.write(f"**Failed:** {len(failed_results)}\n\n")

            if successful_results:
                f.write("## Performance Summary\n\n")
                f.write("| Benchmark | Duration (ms) | Notes |\n")
                f.write("|-----------|---------------|-------|\n")

                for result in successful_results:
                    metadata_str = ", ".join([f"{k}={v}" for k, v in (result.metadata or {}).items()])
                    f.write(f"| {result.name} | {result.duration_ms:.2f} | {metadata_str} |\n")

            if failed_results:
                f.write("\n## Failed Benchmarks\n\n")
                f.write("| Benchmark | Error |\n")
                f.write("|-----------|-------|\n")

                for result in failed_results:
                    f.write(f"| {result.name} | {result.error} |\n")

            f.write("\n## Recommendations\n\n")
            f.write("- Monitor performance trends over time\n")
            f.write("- Set performance baselines for CI/CD\n")
            f.write("- Investigate any failed benchmarks\n")
            f.write("- Consider optimization for slow operations\n")


async def main():
    """Run all benchmarks."""
    benchmarks = AsyncAgentBenchmarks()
    results = await benchmarks.run_all_benchmarks()

    # Print summary
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print("\n📊 Benchmark Summary:")
    print(f"  Total: {len(results)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")

    if successful:
        avg_duration = sum(r.duration_ms for r in successful) / len(successful)
        print(f"  Average Duration: {avg_duration:.2f}ms")

    if failed:
        print(f"  Failed Benchmarks: {[r.name for r in failed]}")


if __name__ == "__main__":
    asyncio.run(main())
