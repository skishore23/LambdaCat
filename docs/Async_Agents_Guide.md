# LambdaCat Async Agents Guide

This guide covers the async agent system in LambdaCat, which provides true parallelism, cognitive capabilities, and production-ready features while preserving the categorical/functional programming principles.

## Overview

The async agent system is built around the **Effect monad**, which represents async, stateful, traced computations. The system provides:

- **True parallelism** via Applicative composition
- **Monadic sequencing** for complex workflows
- **Lens-based state focus** for safe parallel updates
- **Tool adapters** with retries, rate limiting, circuit breaking, streaming, and batch processing
- **Memory and beliefs** for persistent agent state
- **Multi-agent communication** via message bus
- **Observability** with tracing and metrics
- **Persistence** with JSON and SQLite backends (Redis support available)
- **Search integration** with Google, Bing, and Firecrawl providers

## Core Concepts

### Effect Monad

The `Effect[S, A]` monad represents a computation that:
- Takes state `S` and context `Dict[str, Any]`
- Returns `(new_state, trace, result)`
- Is async and composable
- Supports true parallelism

```python
from LambdaCat.agents.core.effect import Effect

# Pure effect
effect = Effect.pure("hello")

# Map over effect
mapped = effect.map(lambda x: x.upper())

# Bind effects
bound = effect.bind(lambda x: Effect.pure(f"processed_{x}"))

# Parallel composition
parallel_effect = Effect.par_mapN(merge_state, effect1, effect2)
```

### Plan DSL

The existing Plan DSL is preserved and compiles to Effects:

```python
from LambdaCat.agents.actions import task, sequence, parallel, choose, focus

# Sequential plan
plan = sequence(
    task("parse_query"),
    task("search_web"),
    task("synthesize")
)

# Parallel plan
plan = parallel(
    task("search_web"),
    task("search_academic")
)

# Conditional plan
plan = choose(
    task("fast_search"),
    task("thorough_search")
)

# Focused plan
plan = focus(
    lens(get_data, set_data),
    task("process_data")
)
```

### Compilation

Plans are compiled to Effects via a natural transformation:

```python
from LambdaCat.agents.core.compile_async import compile_plan_async

# Compile plan to effect
effect = compile_plan_async(plan, actions, merge_state)

# Run effect
final_state, trace, result = await effect.run(initial_state, context)
```

## Usage Examples

### Basic Agent

```python
import asyncio
from LambdaCat.agents.core.async_runtime import run_plan_async
from LambdaCat.agents.actions import task, sequence

async def process_data(state, ctx):
    return {**state, "processed": True}

async def save_results(state, ctx):
    return {**state, "saved": True}

# Define plan
plan = sequence(
    task("process_data"),
    task("save_results")
)

# Define actions
actions = {
    "process_data": process_data,
    "save_results": save_results
}

# Run plan
state = {"data": "initial"}
ctx = {}

final_state, trace, result = await run_plan_async(
    plan=plan,
    actions=actions,
    initial_state=state,
    context=ctx
)
```

### Parallel Processing

```python
async def search_web(state, ctx):
    await asyncio.sleep(0.1)  # Simulate I/O
    return {**state, "web_results": ["result1", "result2"]}

async def search_academic(state, ctx):
    await asyncio.sleep(0.2)  # Simulate I/O
    return {**state, "academic_results": ["paper1", "paper2"]}

# Parallel plan
plan = parallel(
    task("search_web"),
    task("search_academic")
)

actions = {
    "search_web": search_web,
    "search_academic": search_academic
}

# This will run both searches in parallel
final_state, trace, result = await run_plan_async(plan, actions, state, ctx)
```

### LLM Integration

```python
from LambdaCat.agents.tools.llm import create_mock_llm, ask_llm

# Create LLM adapter
llm = create_mock_llm(responses=["AI response"])

# Create effect that uses LLM
effect = ask_llm("What is machine learning?", llm)

# Run effect
state = {"query": "ML question"}
ctx = {"llm": llm}

final_state, trace, result = await effect.run(state, ctx)
```

### Memory and Beliefs

```python
from LambdaCat.agents.cognition.memory import AgentState, remember, update_belief

# Create agent state
state = AgentState()

# Remember information
state = state.remember("last_query", "machine learning")

# Update beliefs
state = state.update_belief("topic_confidence", 0.8)

# Use in effects
async def update_memory(state, ctx):
    agent_state = AgentState.from_dict(state)
    agent_state = agent_state.remember("processed", True)
    return agent_state.to_dict()
```

### Multi-Agent Communication

```python
from LambdaCat.agents.core.bus import create_bus, create_agent_communicator

# Create message bus
bus = await create_bus("request_reply")
await bus.start()

# Create agent communicators
agent1 = await create_agent_communicator("agent1", bus)
agent2 = await create_agent_communicator("agent2", bus)

# Send message
await agent1.send_direct("agent2", "Hello from agent1")

# Receive message
inbox = await agent2.get_inbox()
message = await inbox.get()
print(message.payload)  # "Hello from agent1"
```

### Observability

```python
from LambdaCat.agents.core.instruments import get_observability, span, timer

obs = get_observability()

# Start trace
trace_id = obs.start_trace()

# Create spans
with span("operation", {"key": "value"}):
    # Your code here
    pass

# Record metrics
obs.counter("operations_total", 1.0)
obs.gauge("queue_size", 42.0)
obs.histogram("response_time_ms", 150.0)

# Export data
trace_export = obs.export_trace("json")
metrics_export = obs.export_metrics("json")
```

### Persistence

```python
from LambdaCat.agents.core.persistence import create_backend, PersistenceManager

# Create persistence backend
backend = create_backend("json", base_path="agent_states")
manager = PersistenceManager(backend)

# Save agent state
state = AgentState(data={"key": "value"})
await manager.save_agent_state("agent1", state)

# Load agent state
loaded_state = await manager.load_agent_state("agent1")
```

## Advanced Features

### Lens Integration

Lenses provide safe, focused state manipulation:

```python
from LambdaCat.agents.core.lens_effect import with_lens, dict_lens
from LambdaCat.agents.actions import lens

# Create lens for nested data
data_lens = dict_lens("data")
nested_lens = lens(
    get=lambda s: s["data"]["nested"],
    set=lambda s, v: {**s, "data": {**s["data"], "nested": v}}
)

# Focus effect on sub-state
async def process_nested(state, ctx):
    return {**state, "processed": True}

effect = with_lens(Effect(process_nested), nested_lens)
```

### LLM Streaming and Batch Processing

The LLM adapter supports both streaming and batch processing:

```python
from LambdaCat.agents.tools.llm import create_mock_llm

# Create LLM adapter
llm = create_mock_llm()

# Streaming
async def stream_example():
    async for chunk in llm.stream("Tell me a story"):
        print(chunk, end="", flush=True)

# Batch processing
async def batch_example():
    prompts = [
        "What is machine learning?",
        "Explain quantum computing",
        "Describe renewable energy"
    ]
    responses = await llm.batch_complete(prompts)
    for i, response in enumerate(responses):
        print(f"Response {i+1}: {response.content}")

# Run examples
await stream_example()
await batch_example()
```

### Search Integration

The system includes comprehensive search adapters:

```python
from LambdaCat.agents.tools.search import (
    create_firecrawl_search_adapter,
    create_google_search_adapter,
    create_mock_search_adapter
)

# Firecrawl (recommended for web scraping)
search = create_firecrawl_search_adapter(api_key="your_firecrawl_key")

# Google Custom Search
search = create_google_search_adapter(
    api_key="your_google_key",
    search_engine_id="your_engine_id"
)

# Mock for testing
search = create_mock_search_adapter()

# Search with different providers
results = await search.search("artificial intelligence", num_results=5)

# Multi-provider search
multi_search = create_multi_provider_search_adapter([
    create_firecrawl_search_adapter("key1"),
    create_google_search_adapter("key2", "engine_id")
])
results = await multi_search.search_multiple("machine learning")
```

### Custom Tool Adapters

```python
from LambdaCat.agents.tools.llm import LLMAdapter, LLMClient, LLMConfig

class CustomLLMClient(LLMClient):
    async def complete(self, prompt: str, config: LLMConfig):
        # Your custom implementation
        return LLMResponse(
            content="Custom response",
            model=config.model,
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            finish_reason="stop",
            response_time_ms=100.0
        )

    async def stream(self, prompt: str, config: LLMConfig):
        # Streaming implementation
        for word in "Custom streaming response".split():
            yield word + " "

    async def batch_complete(self, prompts: List[str], config: LLMConfig):
        # Batch implementation
        return [await self.complete(prompt, config) for prompt in prompts]

# Create adapter
client = CustomLLMClient()
adapter = LLMAdapter(client, LLMConfig())
```

### Error Handling

```python
from LambdaCat.agents.core.effect import Effect, Err, Ok

async def risky_operation(state, ctx):
    try:
        # Risky operation
        result = await some_async_operation()
        return (state, [], Ok(result))
    except Exception as e:
        return (state, [{"span": "error", "error": str(e)}], Err(str(e)))

# Effect handles errors gracefully
effect = Effect(risky_operation)
final_state, trace, result = await effect.run(state, ctx)

if isinstance(result, Err):
    print(f"Operation failed: {result.error}")
```

## Testing

The system includes comprehensive test suites:

```python
# Run all tests
pytest tests/test_async_agents.py -v

# Run specific test categories
pytest tests/test_async_agents.py::TestEffectMonad -v
pytest tests/test_async_agents.py::TestLensIntegration -v
```

## Performance Considerations

### Parallelism

- Use `parallel()` for independent operations
- Use `sequence()` for dependent operations
- Use `choose()` for alternative strategies

### Memory Management

- Use lenses for focused state updates
- Use patches for parallel state merging
- Clear scratch variables regularly

### Observability

- Enable tracing for debugging
- Use metrics for monitoring
- Export data for analysis

## Migration from Sync

The async system is backward compatible:

```python
# Old sync code still works
from LambdaCat.agents.runtime import compile_plan

sync_runner = compile_plan(plan, actions)
result = sync_runner(state, ctx)

# New async code
from LambdaCat.agents.core.async_runtime import run_plan_async

final_state, trace, result = await run_plan_async(plan, actions, state, ctx)
```

## Best Practices

1. **Use Effects for async operations** - Don't mix sync and async in the same plan
2. **Leverage parallelism** - Use `parallel()` for independent operations
3. **Handle errors gracefully** - Use Result types and proper error handling
4. **Use lenses for state focus** - Avoid deep state mutations
5. **Enable observability** - Use tracing and metrics for debugging
6. **Test thoroughly** - Use the provided test suites and property-based tests
7. **Follow monad laws** - Ensure your effects are lawful
8. **Use persistence** - Save important state for recovery

## Troubleshooting

### Common Issues

1. **Import errors** - Make sure all dependencies are installed
2. **Async/await issues** - Ensure you're using `await` with async functions
3. **State merging conflicts** - Use patches for parallel state updates
4. **Memory leaks** - Close HTTP sessions and message buses
5. **Test failures** - Check that all required actions are registered

### Debugging

1. **Enable tracing** - Use `get_observability()` to see execution traces
2. **Check logs** - Look at the trace output for errors
3. **Use metrics** - Monitor performance and error rates
4. **Test in isolation** - Use mock adapters for testing

## Further Reading

- [Effect Monad Laws](laws_effect.py) - Mathematical properties
- [Lens Laws](lens_effect.py) - State focus properties  
- [Test Suites](test_async_agents.py) - Usage examples
- [Research Agent Example](research_agent_async.py) - Complete workflow
