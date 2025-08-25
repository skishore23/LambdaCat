# Agent Stack Upgrade Plan (for Kishore)

**Owner:** Kishore  
**Repo:** LambdaCat / agents  
**Date:** 2025-08-25  
**Goal:** Upgrade the current plan-DSL based agent runtime into a production-ready, cognitive, tool-using, *truly parallel* agent stack while preserving the categorical core (functors, Kleisli, lenses).

---

## 0) Executive Summary

- **Keep:** The clean plan DSL (`sequence/parallel/choose/focus/loop`) and monadic style.  
- **Add:** (1) real async concurrency + cancellation; (2) tool adapters (LLMs, web, DB) with retries/rate limits; (3) persistent memory & beliefs; (4) reactive event loop; (5) multi-agent messaging; (6) observability (tracing/metrics); (7) benchmarks & eval.  
- **Principles:** Backward compatible, incremental, tested, with clear interfaces and minimal abstractions.

---

## 1) Current Capabilities (baseline)

- **Plan DSL**: `Task`, `sequence`, `parallel` (structural), `choose`, `focus(lens, ...)`, `loop_while`.
- **Compilation**: formal plan -> executable pipeline (Kleisli over a chosen monad).
- **Monads**: `Result`, `Option`, `Writer`, `State` available in `core/fp`.
- **Plan selection**: run candidate plans and select best via evaluator.
- **Lens-based substate focus**: immutable updates on nested structures.

**Strengths:** principled composition, simple skill registry, clean non-linear patterns.  
**Gaps:** no real parallelism, no tools/LLM adapters, no persistent memory/beliefs, limited observability, no multi-agent messaging, basic control for timeouts/retries.

---

## 2) Target Architecture (high level)

```
agents/
  core/
    runtime.py            # existing
    async_runtime.py      # NEW: async compiler + scheduler
    instruments.py        # NEW: tracing + metrics hooks
    persistence.py        # NEW: state storage interface (KV/JSON/SQLite/Redis)
    bus.py                # NEW: message bus (mailboxes/pub-sub)
  cognition/
    memory.py             # NEW: agent state, lenses, serializers
    beliefs.py            # NEW: weighted beliefs & updates
    policy.py             # NEW: evaluators, utility models
  tools/
    llm.py                # NEW: LLM adapter + retries + streaming
    http.py               # NEW: HTTP client with backoff & budget
    search.py             # NEW: web/search abstraction (pluggable)
  examples/
    research_agent_async.py
    multi_agent_demo.py
    reactive_watchdog.py
```

Design goals: **sync-compatible** (old code runs), **async-native** (new code benefits), **side-effect boundaries** (tools isolated), **observability-first** (structured logs/traces).

---

## 3) Roadmap & Milestones

### Phase A — Runtime & Concurrency (Weeks 1–2)
- Implement `async_runtime.py` with true parallelism (`asyncio.gather`), **timeouts**, **cancellation**, **budgets**.
- Backward compatibility: sync actions still run via thread pool executor when called from async context.
- Add `ParallelPolicy`: `ALL`, `FIRST_COMPLETED`, `N_BEST` (with evaluator).

**Acceptance criteria**
- Parallel branches **truly** overlap in time (measured by traces).
- Cancellation works (slow branches are cancelled on deadline/first-win).
- Unit tests cover timeouts and deterministic cancellation.

### Phase B — Tool Adapters (Weeks 2–3)
- Add `tools/llm.py` and `tools/http.py` with **retries**, **backoff**, **rate-limiters**, **circuit breaker**.
- Provide **sync + async** wrappers so tasks can stay simple.
- Provide budgeted calls: token/time budget tracking.

**Acceptance criteria**
- LLM adapter supports **call**, **stream**, **batch**, retries with jitter.
- Backpressure from rate limiter is respected in parallel plans.

### Phase C — Memory & Beliefs (Weeks 3–4)
- Introduce `cognition/memory.py` (persistent `AgentState`) + `persistence.py` (kv/json/sqlite/redis).
- `beliefs.py`: weighted beliefs (`Dict[str, float]`), simple Bayesian-style updates or log-odds, with decay.
- Lenses for `memory`, `beliefs`, `profile`, `scratch`.

**Acceptance criteria**
- State survives process restarts (file or Redis backend).
- Belief updates are composable actions with property tests.

### Phase D — Reactivity & Multi-Agent (Weeks 4–5)
- `bus.py`: async message bus (mailboxes + pub/sub topics) using `asyncio.Queue`.
- Reactive loop: watch environment/events, trigger plans, persist results.
- Multi-agent demo: 2–3 agents collaborating via topics + shared blackboard (KV).

**Acceptance criteria**
- Messages delivered with at-least-once semantics; backpressure respected.
- Demo shows agents coordinating (e.g., planner + retriever + synthesizer).

### Phase E — Observability & Eval (Week 5)
- `instruments.py`: structured logs, spans, counters; a simple timeline viewer.
- Add **policy evaluators** and **benchmarks** (latency, cost, quality).

**Acceptance criteria**
- Run reports include wall time per node, tool spend, token usage, success rates.
- Benchmarks produce CSV/MD summaries reproducibly.

---

## 4) API Deltas (minimal and backward compatible)

### 4.1 Action Signatures

- **Sync** action: `def action(state, ctx=None) -> state'`
- **Async** action: `async def action(state, ctx=None) -> state'`

Compiler handles both; old sync actions require no changes.

### 4.2 Parallel with Policies

```python
@dataclass(frozen=True)
class ParallelSpec:
    branches: list[Any]                     # subplans
    policy: str = "ALL"                     # "ALL" | "FIRST_COMPLETED" | "N_BEST"
    n_best: int = 1                         # if policy == "N_BEST"
    timeout_s: float | None = None          # global timeout for the group
```

---

## 5) Code: Async Runtime (core)

```python
# agents/core/async_runtime.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Coroutine
import asyncio
import contextlib

State = Any
Ctx = Any
Action = Callable[[State, Ctx], State] | Callable[[State, Ctx], Awaitable[State]]

async def _maybe_await(x):
    return await x if asyncio.iscoroutine(x) else x

async def call_action(fn: Action, s: State, ctx: Ctx) -> State:
    res = fn(s, ctx)  # sync or coroutine
    return await _maybe_await(res)

async def sequence(exec_nodes: list[Callable[[State, Ctx], Awaitable[State]]], s: State, ctx: Ctx) -> State:
    cur = s
    for node in exec_nodes:
        cur = await node(cur, ctx)
    return cur

@dataclass(frozen=True)
class ParallelSpec:
    branches: list[Callable[[State, Ctx], Awaitable[State]]]
    policy: str = "ALL"             # "ALL" | "FIRST_COMPLETED" | "N_BEST"
    n_best: int = 1
    timeout_s: float | None = None

async def parallel(spec: ParallelSpec, s: State, ctx: Ctx, evaluator: Callable[[State], float] | None = None) -> State:
    async def run_branch(fn):
        return await fn(s, ctx)

    tasks = [asyncio.create_task(run_branch(b)) for b in spec.branches]
    try:
        if spec.policy == "ALL":
            done, pending = await asyncio.wait(tasks, timeout=spec.timeout_s)
            for p in pending: p.cancel()
            # simple merge: last wins; override with a combiner if needed
            last = None
            for t in done:
                last = t.result()
            return last if last is not None else s

        if spec.policy == "FIRST_COMPLETED":
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=spec.timeout_s)
            for p in pending: p.cancel()
            return next(iter(done)).result()

        if spec.policy == "N_BEST":
            done, pending = await asyncio.wait(tasks, timeout=spec.timeout_s)
            for p in pending: p.cancel()
            results = [t.result() for t in done if not t.cancelled()]
            if not results: return s
            scored = sorted(results, key=(evaluator or (lambda x: 0.0)), reverse=True)
            return scored[0]
    finally:
        for t in tasks:
            with contextlib.suppress(Exception):
                if not t.done():
                    t.cancel()
```

**Notes**
- Deterministic cancellation on policy satisfaction.
- Pluggable **combiner** can be added (e.g., monoidal merge of branches).

---

## 6) Code: Tool Adapter (LLM) with Retries/Rate Limits

```python
# agents/tools/llm.py
from __future__ import annotations
from typing import Any, Dict, Optional, Callable
import asyncio, time, random

class RateLimiter:
    def __init__(self, rate_per_s: float):
        self.period = 1.0 / rate_per_s
        self._next = time.perf_counter()

    async def acquire(self):
        now = time.perf_counter()
        if now < self._next:
            await asyncio.sleep(self._next - now)
        self._next = max(self._next + self.period, time.perf_counter())

async def with_retries(coro_factory: Callable[[], asyncio.Future], retries=3, base=0.5, cap=4.0):
    for i in range(retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            if i == retries: raise
            backoff = min(cap, base * (2 ** i)) * (1 + 0.1 * random.random())
            await asyncio.sleep(backoff)

class LLM:
    def __init__(self, client, rate_per_s: float = 3.0):
        self.client = client
        self.limiter = RateLimiter(rate_per_s)

    async def complete(self, prompt: str, **opts) -> str:
        await self.limiter.acquire()
        async def make_call():
            # Example: OpenAI-like async client; replace with real call
            return await self.client.generate(prompt=prompt, **opts)
        return await with_retries(make_call, retries=opts.get("retries", 3))
```

**Integration as a Task**

```python
# register as action
async def ask_llm(state, ctx):
    llm: LLM = ctx["llm"]
    q = state.get("question", "")
    a = await llm.complete(f"Answer succinctly: {q}")
    return {**state, "answer": a}
```

---

## 7) Code: Memory & Beliefs (State + Lenses + Persistence)

```python
# agents/cognition/memory.py
from dataclasses import dataclass, field, asdict
from typing import Any, Dict

@dataclass(frozen=True)
class AgentState:
    data: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    beliefs: Dict[str, float] = field(default_factory=dict)  # weighted

def remember(key: str, value: Any, s: AgentState, ctx=None) -> AgentState:
    m = dict(s.memory); m[key] = value
    return AgentState(data=s.data, memory=m, beliefs=s.beliefs)

def update_belief(prop: str, delta_logit: float, s: AgentState, ctx=None) -> AgentState:
    w = s.beliefs.get(prop, 0.0) + delta_logit
    b = dict(s.beliefs); b[prop] = w
    return AgentState(data=s.data, memory=s.memory, beliefs=b)
```

```python
# agents/core/persistence.py
import json, os
from typing import Callable
from dataclasses import asdict

def save_json(path: str, state) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(state), f, ensure_ascii=False, indent=2)

def load_json(path: str, constructor: Callable):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return constructor(**data)
```

**Usage in a Plan**

```python
# actions
def perceive_env(s: AgentState, ctx=None) -> AgentState:
    env = (ctx or {}).get("env", {})
    return remember("last_env", env, s, ctx)

def agent_step(s: AgentState, ctx=None) -> AgentState:
    # toy: belief increases if temperature is high
    temp = s.memory.get("last_env", {}).get("temperature", 0.0)
    return update_belief("is_hot", 0.2 if temp > 25 else -0.1, s, ctx)
```

---

## 8) Code: Reactive Loop & Bus (Multi-Agent)

```python
# agents/core/bus.py
import asyncio
from collections import defaultdict
from typing import Any, Dict, Callable

class Bus:
    def __init__(self):
        self.topics: Dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def subscribe(self, topic: str) -> asyncio.Queue:
        q = asyncio.Queue()
        self.topics[topic].append(q)
        return q

    async def publish(self, topic: str, msg: Any):
        for q in self.topics.get(topic, []):
            await q.put(msg)
```

```python
# reactive loop
async def agent_loop(name: str, plan_fn, initial_state, ctx, inbox: asyncio.Queue, bus: Bus):
    state = initial_state
    while True:
        msg = await inbox.get()
        if msg == "__STOP__":
            break
        # enrich ctx with message/environment
        ctx2 = dict(ctx); ctx2["msg"] = msg
        state = await plan_fn(state, ctx2)
        await bus.publish(f"{name}:state", state)
```

```python
# wiring a small system
async def run_system():
    bus = Bus()
    inbox_a = await bus.subscribe("topic:tasks")
    inbox_b = await bus.subscribe("topic:tasks")

    async def plan_a(s, ctx):  # wraps sequence/parallel with async runtime
        # ... call async plan here
        return s

    async def plan_b(s, ctx):
        # ... another plan
        return s

    task_a = asyncio.create_task(agent_loop("A", plan_a, AgentState(), {"llm": ...}, inbox_a, bus))
    task_b = asyncio.create_task(agent_loop("B", plan_b, AgentState(), {"llm": ...}, inbox_b, bus))

    await bus.publish("topic:tasks", {"cmd": "search", "q": "graph transformers"})
    await asyncio.sleep(2)
    await bus.publish("topic:tasks", "__STOP__")
    await bus.publish("topic:tasks", "__STOP__")
    await asyncio.gather(task_a, task_b)
```

---

## 9) Code: Observability

```python
# agents/core/instruments.py
import time
from contextlib import contextmanager

@contextmanager
def span(name: str, logs: list):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = (time.perf_counter() - t0) * 1000
        logs.append({"span": name, "ms": round(dt, 2)})
```

**Use inside runtime** (wrap each node/action). Export logs per run to JSON/CSV for later analysis.

---

## 10) Evaluation & Benchmarks

- **Latency:** sequential vs async parallel plans on synthetic I/O-bound tasks.
- **Cost:** token usage (LLM), request counts, retry rates.
- **Quality:** evaluator scores vs baselines (e.g., unit tests with expected summaries).
- **Stability:** chaos tests (random faults, rate limit spikes).

Artifacts: `bench/` with reproducible scripts; results summarized in `bench/README.md` and CSV.

---

## 11) Security & Safety

- Tool calls run behind **budgets** (time/token) and **domain allowlists**.
- Sanitize inputs/outputs before persistence.
- Optional **sandbox** for Python tool execution (subprocess + seccomp where applicable).

---

## 12) Migration Strategy

- Keep the existing DSL untouched; the new async runtime compiles the same AST.
- Start by re-implementing current examples with async runtime (no behavior change), then enable **true parallel** + timeouts where beneficial.
- Gradually introduce memory/belief actions. Tie persistence at plan entry/exit.

---

## 13) Deliverables Checklist

- [ ] `core/async_runtime.py` with tests
- [ ] `tools/llm.py` + `http.py` with retries/limits & tests
- [ ] `cognition/memory.py` + `beliefs.py` + lenses
- [ ] `core/persistence.py` with JSON + Redis backends
- [ ] `core/bus.py` + reactive examples
- [ ] `core/instruments.py` + run reports
- [ ] Examples: research agent (async, tool-using), multi-agent demo, reactive watchdog
- [ ] Benchmarks + CI job
- [ ] Docs: migration guide + API reference

---

## 14) Minimal Working Example (end-to-end)

```python
# examples/research_agent_async.py (sketch)
import asyncio
from agents.core.async_runtime import sequence, ParallelSpec, parallel, call_action
from agents.tools.llm import LLM
from agents.cognition.memory import AgentState, remember

async def parse(state, ctx):   # cheap local
    q = state["query"]; kws = q.split()
    return {**state, "kws": kws}

async def search_web(state, ctx):  # I/O bound
    await asyncio.sleep(0.3)  # placeholder for HTTP call
    return remember("web_hits", ["url1","url2"], AgentState(**state))

async def search_scholar(state, ctx):
    await asyncio.sleep(0.5)
    return remember("scholar_hits", ["doi1","doi2"], AgentState(**state))

async def synthesize(state, ctx):
    llm: LLM = ctx["llm"]
    hits = state.get("web_hits", []) + state.get("scholar_hits", [])
    ans = await llm.complete(f"Synthesize from: {hits}")
    return {**state, "answer": ans}

async def run_agent(q: str, llm: LLM):
    s = {"query": q}
    ctx = {"llm": llm}

    async def branch_web(s, ctx): return await call_action(search_web, s, ctx)
    async def branch_sch(s, ctx): return await call_action(search_scholar, s, ctx)

    s = await call_action(parse, s, ctx)
    s = await parallel(ParallelSpec([branch_web, branch_sch], policy="ALL", timeout_s=2.0), s, ctx)
    s = await call_action(synthesize, s, ctx)
    return s

# asyncio.run(run_agent("graph transformer interpretability", llm=LLM(client=...)))
```

---

## 15) Risks & Mitigations

- **Async complexity** → keep compiler small; extensive tests; constrain APIs.
- **Tool cost drift** → budgets & instrumentation; CI smoke tests with fake clients.
- **State explosion** → lenses + size limits; periodic compaction.
- **Overfitting DSL** → keep escape hatches (custom node, custom combiner).

---

## 16) Next Actions (this week)

1. Implement `core/async_runtime.py` with tests for `sequence` and `parallel` (ALL/FIRST_COMPLETED).
2. Add `tools/llm.py` with in-memory fake client; wire example.
3. Add `cognition/memory.py` and simple JSON persistence; demo survival across runs.
4. Port the existing “research” example to async and measure speedup.
5. Write developer docs for adding an async `Task` and instrumenting it.

---

**End of document.**
