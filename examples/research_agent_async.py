#!/usr/bin/env python3
"""
Research Agent with Async Runtime Demo

This example demonstrates the new async agent system with:
- True parallelism via Effect monad
- LLM integration with retries and rate limiting
- HTTP requests with backoff
- Memory and belief management
- Observability and tracing
"""

import asyncio
import json
from typing import Any

from LambdaCat.agents.actions import parallel, sequence, task
from LambdaCat.agents.cognition.memory import AgentState
from LambdaCat.agents.core.bus import create_agent_communicator, create_bus

# Import the new async agent system
from LambdaCat.agents.core.compile_async import run_plan
from LambdaCat.agents.core.instruments import get_observability, span
from LambdaCat.agents.core.patch import patch_combine
from LambdaCat.agents.core.persistence import PersistenceManager, create_backend
from LambdaCat.agents.tools.http import create_http_adapter
from LambdaCat.agents.tools.llm import create_mock_llm


# Define the research agent actions
async def parse_query(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Parse the research query into keywords."""
    query = state.get("query", "")
    keywords = query.lower().split()

    new_state = dict(state)
    new_state["keywords"] = keywords
    new_state["parsed"] = True

    return new_state


async def search_web(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Search the web for information."""
    query = state.get("query", "")
    keywords = state.get("keywords", [])

    # Simulate web search with delay
    await asyncio.sleep(0.2)

    # Mock search results
    results = [
        {
            "title": f"Web result for {query}",
            "url": f"https://example.com/{keyword}",
            "snippet": f"Information about {keyword} from web search"
        }
        for keyword in keywords[:3]  # Limit to 3 results
    ]

    new_state = dict(state)
    new_state["web_results"] = results
    new_state["web_searched"] = True

    return new_state


async def search_academic(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Search academic databases."""
    query = state.get("query", "")
    keywords = state.get("keywords", [])

    # Simulate academic search with delay
    await asyncio.sleep(0.3)

    # Mock academic results
    results = [
        {
            "title": f"Academic paper on {query}",
            "authors": ["Dr. Smith", "Dr. Jones"],
            "abstract": f"Research findings on {keyword}",
            "doi": f"10.1000/{keyword}"
        }
        for keyword in keywords[:2]  # Limit to 2 results
    ]

    new_state = dict(state)
    new_state["academic_results"] = results
    new_state["academic_searched"] = True

    return new_state


async def synthesize_findings(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Synthesize findings using LLM."""
    llm = ctx.get("llm")
    if not llm:
        raise ValueError("LLM not provided in context")

    web_results = state.get("web_results", [])
    academic_results = state.get("academic_results", [])
    query = state.get("query", "")

    # Prepare synthesis prompt
    web_text = "\n".join([f"- {r['title']}: {r['snippet']}" for r in web_results])
    academic_text = "\n".join([f"- {r['title']} by {', '.join(r['authors'])}: {r['abstract']}" for r in academic_results])

    prompt = f"""
    Research Query: {query}

    Web Sources:
    {web_text}

    Academic Sources:
    {academic_text}

    Please synthesize these findings into a comprehensive summary.
    """

    # Use LLM to synthesize
    response = await llm.complete(prompt)

    new_state = dict(state)
    new_state["synthesis"] = response.content
    new_state["synthesized"] = True

    return new_state


async def update_beliefs(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Update agent beliefs based on findings."""
    # Convert to AgentState for belief updates
    agent_state = AgentState.from_dict(state)

    # Update beliefs based on synthesis quality
    synthesis = state.get("synthesis", "")
    if len(synthesis) > 100:
        # High-quality synthesis increases confidence
        agent_state = agent_state.update_belief("research_quality", 0.5)
    else:
        # Low-quality synthesis decreases confidence
        agent_state = agent_state.update_belief("research_quality", -0.3)

    # Update belief about topic complexity
    keywords = state.get("keywords", [])
    if len(keywords) > 5:
        agent_state = agent_state.update_belief("topic_complexity", 0.2)

    # Convert back to dict
    new_state = agent_state.to_dict()
    new_state.update(state)  # Preserve original state

    return new_state


async def save_results(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Save research results."""
    persistence = ctx.get("persistence")
    if not persistence:
        # No persistence available, just return state
        return state

    # Save results
    results = {
        "query": state.get("query"),
        "synthesis": state.get("synthesis"),
        "web_results": state.get("web_results", []),
        "academic_results": state.get("academic_results", []),
        "beliefs": state.get("beliefs", {}),
        "timestamp": asyncio.get_event_loop().time()
    }

    await persistence.save_checkpoint(f"research_{state.get('query', 'unknown')}", results)

    new_state = dict(state)
    new_state["saved"] = True

    return new_state


# Define the research plan
def create_research_plan() -> Any:
    """Create the research agent plan."""
    return sequence(
        task("parse_query"),
        parallel(
            task("search_web"),
            task("search_academic")
        ),
        task("synthesize_findings"),
        task("update_beliefs"),
        task("save_results")
    )


# Define action registry
def create_action_registry() -> dict[str, Any]:
    """Create the action registry."""
    return {
        "parse_query": parse_query,
        "search_web": search_web,
        "search_academic": search_academic,
        "synthesize_findings": synthesize_findings,
        "update_beliefs": update_beliefs,
        "save_results": save_results,
    }


async def run_research_agent(query: str) -> dict[str, Any]:
    """Run the research agent with the given query."""
    # Create components
    llm = create_mock_llm(
        responses=[
            f"This is a comprehensive synthesis of research findings about {query}. "
            f"The evidence suggests that this topic is complex and multifaceted, "
            f"requiring further investigation and analysis."
        ]
    )

    http_adapter = create_http_adapter()

    # Create persistence
    persistence_backend = create_backend("json", base_path="research_results")
    persistence = PersistenceManager(persistence_backend)

    # Create observability
    obs = get_observability()
    trace_id = obs.start_trace()

    # Create context
    context = {
        "llm": llm,
        "http": http_adapter,
        "persistence": persistence,
        "trace_id": trace_id
    }

    # Create initial state
    initial_state = {
        "query": query,
        "keywords": [],
        "web_results": [],
        "academic_results": [],
        "synthesis": "",
        "beliefs": {},
        "parsed": False,
        "web_searched": False,
        "academic_searched": False,
        "synthesized": False,
        "saved": False
    }

    # Create plan and action registry
    plan = create_research_plan()
    actions = create_action_registry()

    # Run the plan
    with span("research_agent", {"query": query}):
        final_state, trace, result = await run_plan(
            plan=plan,
            actions=actions,
            initial_state=initial_state,
            context=context,
            merge_state=patch_combine
        )

    # Export observability data
    trace_export = obs.export_trace("json")
    metrics_export = obs.export_metrics("json")

    print("=== Research Agent Results ===")
    print(f"Query: {query}")
    print(f"Synthesis: {final_state.get('synthesis', 'No synthesis available')}")
    print(f"Web Results: {len(final_state.get('web_results', []))}")
    print(f"Academic Results: {len(final_state.get('academic_results', []))}")
    print(f"Beliefs: {final_state.get('beliefs', {})}")
    print(f"Trace ID: {trace_id}")

    # Save observability data
    with open(f"research_trace_{trace_id}.json", "w") as f:
        json.dump(json.loads(trace_export), f, indent=2)

    with open(f"research_metrics_{trace_id}.json", "w") as f:
        json.dump(json.loads(metrics_export), f, indent=2)

    return final_state


async def run_multi_agent_demo():
    """Run a multi-agent demo with communication."""
    # Create message bus
    bus = await create_bus("request_reply")
    await bus.start()

    try:
        # Create agent communicators
        researcher = await create_agent_communicator("researcher", bus)
        synthesizer = await create_agent_communicator("synthesizer", bus)

        # Define agent plans
        async def researcher_plan(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
            """Researcher agent plan."""
            query = state.get("query", "")

            # Search for information
            web_results = await search_web(state, ctx)
            academic_results = await search_academic(state, ctx)

            # Send results to synthesizer
            await researcher.send_message(
                "synthesis_request",
                {
                    "query": query,
                    "web_results": web_results.get("web_results", []),
                    "academic_results": academic_results.get("academic_results", [])
                }
            )

            return {**state, **web_results, **academic_results}

        async def synthesizer_plan(state: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
            """Synthesizer agent plan."""
            # Get inbox
            inbox = await synthesizer.get_inbox()

            # Process messages
            while True:
                try:
                    message = await asyncio.wait_for(inbox.get(), timeout=1.0)

                    if message.topic == "synthesis_request":
                        payload = message.payload

                        # Synthesize findings
                        synthesis = await synthesize_findings(
                            {"query": payload["query"], "web_results": payload["web_results"], "academic_results": payload["academic_results"]},
                            ctx
                        )

                        # Send synthesis back
                        await synthesizer.send_direct(
                            message.sender,
                            {"synthesis": synthesis.get("synthesis", "")}
                        )

                        return {**state, "synthesis": synthesis.get("synthesis", "")}

                except asyncio.TimeoutError:
                    break

            return state

        # Run agents
        researcher_task = asyncio.create_task(
            researcher_plan({"query": "artificial intelligence ethics"}, {"llm": create_mock_llm()})
        )

        synthesizer_task = asyncio.create_task(
            synthesizer_plan({}, {"llm": create_mock_llm()})
        )

        # Wait for completion
        await asyncio.gather(researcher_task, synthesizer_task)

        print("=== Multi-Agent Demo Completed ===")

    finally:
        await bus.stop()


async def main():
    """Main demo function."""
    print("LambdaCat Async Agent System Demo")
    print("=" * 40)

    # Single agent demo
    print("\n1. Single Agent Research Demo")
    print("-" * 30)

    queries = [
        "machine learning interpretability",
        "quantum computing applications",
        "sustainable energy solutions"
    ]

    for query in queries:
        print(f"\nResearching: {query}")
        result = await run_research_agent(query)
        print(f"Completed: {result.get('synthesized', False)}")

    # Multi-agent demo
    print("\n2. Multi-Agent Communication Demo")
    print("-" * 30)

    await run_multi_agent_demo()

    print("\nDemo completed! Check the generated files for detailed results.")


if __name__ == "__main__":
    asyncio.run(main())
