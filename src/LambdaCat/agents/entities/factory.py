"""Factory functions for creating agent entities."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Callable, TypeVar

from ..cognition.memory import AgentState
from ..core.bus import Message, MessageBus
from ..core.compile_async import AsyncCompiler
from .agent import AgentEntity
from .bus import SimpleBus
from .goals import Goal
from .policy import SimpleIntentionPolicy

S = TypeVar("S")  # State type


def create_agent_entity(
    agent_id: str,
    goals: list[Goal[S]],
    skills: dict[str, Callable[[S, dict[str, object]], S | asyncio.Future[S]]],
    goal_to_plan: dict[str, object],  # Plan DSL ASTs
    bus: MessageBus | None = None,
    persistence_path: str | None = None,
    context: dict[str, object] | None = None
) -> AgentEntity[S]:
    """Create an agent entity with the given configuration."""
    if bus is None:
        bus = MessageBus()

    inbox: asyncio.Queue[Message[object]] = asyncio.Queue()

    if persistence_path:
        def persist_func(state: AgentState[S]) -> None:
            os.makedirs(os.path.dirname(persistence_path), exist_ok=True)
            with open(persistence_path, "w", encoding="utf-8") as f:
                json.dump({
                    "data": state.data,
                    "memory": state.memory,
                    "beliefs": state.beliefs,
                    "scratch": state.scratch
                }, f, indent=2)
    else:
        def persist_func(state: AgentState[S]) -> None:
            pass

    policy = SimpleIntentionPolicy(goal_to_plan)
    runtime = AsyncCompiler(actions=skills)
    state = AgentState()

    return AgentEntity(
        aid=agent_id,
        state=state,
        goals=goals,
        skills=skills,
        policy=policy,
        runtime=runtime,
        inbox=inbox,
        bus=bus,
        persist=persist_func,
        context=context or {}
    )


def create_simple_bus() -> SimpleBus:
    """Create a simple message bus."""
    return SimpleBus()


async def run_multi_agent_system(
    agents: list[AgentEntity[object]],
    bus: MessageBus,
    duration: float = 10.0
) -> None:
    """Run a multi-agent system for a specified duration."""
    tasks = [asyncio.create_task(agent.run()) for agent in agents]

    try:
        await asyncio.sleep(duration)
    finally:
        for agent in agents:
            await agent.stop()
        await asyncio.gather(*tasks, return_exceptions=True)
