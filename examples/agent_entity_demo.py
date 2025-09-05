"""Demo of agent entities - persistent agents with goals and intentions."""

import asyncio
from typing import Any

from src.LambdaCat.agents.actions import Task, sequence
from src.LambdaCat.agents.core.bus import Message
from src.LambdaCat.agents.entities import (
    Goal,
    create_agent_entity,
)


async def research_skill(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Research skill that simulates web search."""
    query = state.get("query", "")
    print(f"Researching: {query}")

    results = [
        f"Research result 1 for '{query}'",
        f"Research result 2 for '{query}'",
        f"Research result 3 for '{query}'"
    ]

    return {**state, "search_results": results}


async def synthesize_skill(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Synthesis skill that combines research results."""
    results = state.get("research_results", [])
    query = state.get("query", "")

    print(f"Synthesizing {len(results)} results for: {query}")

    synthesis = f"Based on {len(results)} research sources, here's what I found about '{query}':\n"
    synthesis += "\n".join(f"- {result}" for result in results)

    return {**state, "synthesis": synthesis, "success": True}


async def review_skill(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Review skill that evaluates the synthesis."""
    synthesis = state.get("synthesis", "")

    print("Reviewing synthesis quality...")

    quality_score = min(1.0, len(synthesis) / 100.0)

    return {**state, "quality_score": quality_score, "reviewed": True}


async def watchdog_skill(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Watchdog skill that monitors for issues."""
    event = state.get("current_event", {})
    event_type = event.get("type", "unknown")

    print(f"Monitoring event: {event_type}")

    if event_type == "alert":
        severity = event.get("severity", "low")
        print(f"Alert detected with severity: {severity}")
        return {**state, "alert_handled": True, "severity": severity}
    else:
        print("No issues detected")
        return {**state, "status": "normal"}


async def create_research_agent() -> Any:
    """Create a research agent entity."""
    research_goal = Goal(
        name="research_topic",
        params={"max_results": 5, "quality_threshold": 0.8},
        priority=0.9
    )

    skills = {
        "research": research_skill,
        "synthesize": synthesize_skill,
        "review": review_skill
    }

    research_plan = sequence(
        Task("research"),
        Task("synthesize"),
        Task("review")
    )

    agent = create_agent_entity(
        agent_id="research_agent",
        goals=[research_goal],
        skills=skills,
        goal_to_plan={"research_topic": research_plan},
        context={"max_retries": 3, "timeout": 30.0}
    )

    return agent


async def create_watchdog_agent() -> Any:
    """Create a watchdog agent entity."""
    monitor_goal = Goal(
        name="monitor_events",
        params={"alert_threshold": 0.7, "check_interval": 1.0},
        priority=0.8
    )

    skills = {"watchdog": watchdog_skill}

    monitor_plan = sequence(Task("watchdog"))

    agent = create_agent_entity(
        agent_id="watchdog_agent",
        goals=[monitor_goal],
        skills=skills,
        goal_to_plan={"monitor_events": monitor_plan},
        context={"monitoring_active": True}
    )

    return agent


async def run_agent_entity_demo():
    """Run the agent entity demonstration."""
    print("Starting Agent Entity Demo")
    print("=" * 50)

    research_agent = await create_research_agent()
    watchdog_agent = await create_watchdog_agent()

    print(f"Created {research_agent.aid}")
    print(f"Created {watchdog_agent.aid}")
    print()

    print("Starting agents...")
    research_task = asyncio.create_task(research_agent.run())
    watchdog_task = asyncio.create_task(watchdog_agent.run())

    await asyncio.sleep(0.1)

    print("\nSending research request...")
    research_message = Message.create(
        topic="research",
        payload={
            "observation": {
                "query": "artificial intelligence trends 2024",
                "type": "research_request"
            }
        },
        sender="user"
    )
    await research_agent.inbox.put(research_message)

    print("\nSending monitoring event...")
    monitor_message = Message.create(
        topic="monitoring",
        payload={
            "observation": {
                "type": "alert",
                "severity": "high",
                "message": "System overload detected"
            }
        },
        sender="system"
    )
    await watchdog_agent.inbox.put(monitor_message)

    print("\nLetting agents process...")
    await asyncio.sleep(2.0)

    print("\nStopping agents...")
    await research_agent.stop()
    await watchdog_agent.stop()

    await asyncio.gather(research_task, watchdog_task, return_exceptions=True)

    print("\nResults:")
    print(f"Research Agent Memory: {len(research_agent.state.memory)} entries")
    print(f"Research Agent Beliefs: {len(research_agent.state.beliefs)} beliefs")
    print(f"Watchdog Agent Memory: {len(watchdog_agent.state.memory)} entries")
    print(f"Watchdog Agent Beliefs: {len(watchdog_agent.state.beliefs)} beliefs")

    print("\nResearch Agent Memory Sample:")
    for key, value in list(research_agent.state.memory.items())[:3]:
        print(f"  {key}: {str(value)[:100]}...")

    print("\nWatchdog Agent Memory Sample:")
    for key, value in list(watchdog_agent.state.memory.items())[:3]:
        print(f"  {key}: {str(value)[:100]}...")

    print("\nAgent Entity Demo Complete!")


async def run_multi_agent_coordination_demo():
    """Run a multi-agent coordination demonstration."""
    print("\nMulti-Agent Coordination Demo")
    print("=" * 50)

    agents = []
    specializations = [
        ("AI_research", "artificial intelligence"),
        ("ML_research", "machine learning"),
        ("NLP_research", "natural language processing")
    ]

    for spec_name, topic in specializations:
        goal = Goal(
            name=f"research_{spec_name}",
            params={"topic": topic, "depth": "comprehensive"},
            priority=0.8
        )

        skills = {
            "research": research_skill,
            "synthesize": synthesize_skill
        }

        plan = sequence(Task("research"), Task("synthesize"))

        agent = create_agent_entity(
            agent_id=f"{spec_name}_agent",
            goals=[goal],
            skills=skills,
            goal_to_plan={f"research_{spec_name}": plan}
        )

        agents.append(agent)

    print(f"Created {len(agents)} specialized research agents")

    tasks = [asyncio.create_task(agent.run()) for agent in agents]

    await asyncio.sleep(0.1)

    for i, agent in enumerate(agents):
        message = Message.create(
            topic="research",
            payload={
                "observation": {
                    "query": f"Latest trends in {specializations[i][1]}",
                    "type": "research_request"
                }
            },
            sender="coordinator"
        )
        await agent.inbox.put(message)

    print("\nSent research requests to all agents...")

    await asyncio.sleep(3.0)

    for agent in agents:
        await agent.stop()

    await asyncio.gather(*tasks, return_exceptions=True)

    print("\nCoordination Results:")
    for agent in agents:
        print(f"{agent.aid}: {len(agent.state.memory)} memory entries, {len(agent.state.beliefs)} beliefs")

    print("\nMulti-Agent Coordination Demo Complete!")


if __name__ == "__main__":
    print("Agent Entity System Demo")
    print("This demonstrates persistent agents with goals, beliefs, and intentions")
    print()

    asyncio.run(run_agent_entity_demo())
    asyncio.run(run_multi_agent_coordination_demo())
