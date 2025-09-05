"""Agent entity - persistent agents with goals, beliefs, and intentions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

from ..cognition.memory import AgentState
from ..core.bus import Message, MessageBus
from ..core.compile_async import AsyncCompiler
from .goals import Goal
from .policy import IntentionPolicy

S = TypeVar("S")  # State type


@dataclass
class AgentEntity(Generic[S]):
    """A persistent agent entity with goals, beliefs, and intentions."""

    aid: str
    state: AgentState[S]
    goals: list[Goal[S]]
    skills: dict[str, Callable[[S, dict[str, object]], S | asyncio.Future[S]]]
    policy: IntentionPolicy[S]
    runtime: AsyncCompiler[S, dict[str, object]]
    inbox: asyncio.Queue[Message[object]]
    bus: MessageBus
    persist: Callable[[AgentState[S]], None]
    context: dict[str, object] = field(default_factory=dict)
    running: bool = False

    async def perceive(self, message: Message[object]) -> None:
        """Process incoming messages and update beliefs."""
        if isinstance(message.payload, dict) and "observation" in message.payload:
            obs = message.payload["observation"]
            self.state = self.state.update_belief(
                f"obs_{message.timestamp}",
                delta_logit=0.1
            )
            self.state = self.state.remember(f"last_obs_{message.timestamp}", obs)

    async def act_once(self) -> None:
        """Execute one action cycle: propose intentions, select, and execute."""
        intentions = self.policy.propose_intentions(
            self.goals,
            self.state,
            self.context
        )

        if not intentions:
            return

        selected_intention = self.policy.select_action(
            self.state,
            intentions,
            self.context
        )

        try:
            initial_state = {
                "beliefs": self.state.data,
                "memory": self.state.memory,
                "goals": [goal.name for goal in self.goals],
                "intention": selected_intention.goal.name
            }

            effect = self.runtime.compile(selected_intention.plan_ast)
            final_state, trace, result = await effect.run(initial_state, self.context)

            self.state = self.state.remember(
                f"execution_{asyncio.get_event_loop().time()}",
                {
                    "intention": selected_intention.goal.name,
                    "result": result,
                    "trace": trace
                }
            )

            if isinstance(result, dict) and "success" in result:
                success = result["success"]
                self.state = self.state.update_belief(
                    f"execution_success_{selected_intention.goal.name}",
                    success,
                    delta_logit=0.2 if success else -0.2
                )

        except Exception as e:
            self.state = self.state.remember(
                f"error_{asyncio.get_event_loop().time()}",
                {
                    "intention": selected_intention.goal.name,
                    "error": str(e)
                }
            )
            self.state = self.state.update_belief(
                f"execution_error_{selected_intention.goal.name}",
                str(e),
                delta_logit=-0.3
            )

    async def run(self) -> None:
        """Main agent loop: perceive messages and act."""
        self.running = True

        while self.running:
            try:
                message = await asyncio.wait_for(self.inbox.get(), timeout=1.0)

                if isinstance(message.payload, str) and message.payload == "__STOP__":
                    break

                await self.perceive(message)
                await self.act_once()
                self.persist(self.state)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.state = self.state.remember(
                    f"error_{asyncio.get_event_loop().time()}",
                    {"error": str(e), "type": "run_loop"}
                )

    async def stop(self) -> None:
        """Stop the agent."""
        self.running = False
        stop_message = Message.create(
            topic="control",
            payload="__STOP__",
            sender=self.aid
        )
        await self.inbox.put(stop_message)

    def add_goal(self, goal: Goal[S]) -> None:
        """Add a new goal to the agent."""
        self.goals.append(goal)

    def remove_goal(self, goal_name: str) -> bool:
        """Remove a goal by name."""
        for i, goal in enumerate(self.goals):
            if goal.name == goal_name:
                del self.goals[i]
                return True
        return False

    def get_goal(self, goal_name: str) -> Goal[S] | None:
        """Get a goal by name."""
        for goal in self.goals:
            if goal.name == goal_name:
                return goal
        return None
