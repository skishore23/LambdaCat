# Agent Entities vs Plan Pipelines — Spec & Minimal Implementation

**Owner:** Kishore  
**Date:** 2025-08-25  
**Scope:** Define *agents as entities* and show how to integrate them with the existing plan DSL (sequence/parallel/choose/focus/loop) as the *intention executor*. Includes code skeletons.

---

## What an agent is (ENTITY)

> *Agreed. What you have now is a **planner**. An **agent** (entity) is **persistent**: it has identity, goals, memory/beliefs, perceptions, policies, capabilities, and it acts over time (and with others).*

**Agent = (Identity, Goals, Beliefs/Memory, Perception, Capabilities, Policy, Scheduler, Runtime, Mailbox, Persistence).**

- **Beliefs/Memory**: long-lived knowledge (state + weights/uncertainty).
- **Goals/Utility**: desires + constraints; produce candidate intentions.
- **Policy/Scheduler**: pick which intention to pursue now (budget, risk, time).
- **Perception**: turn environment/messages into events & belief updates.
- **Capabilities**: tools/skills it can invoke (LLMs, HTTP, DB, code).
- **Runtime**: your existing **plan DSL** (sequence/parallel/choose/focus) executing **chosen intentions**.
- **Mailbox/Bus**: messages to/from other agents & environment.
- **Persistence/Identity**: survives restarts; stable id/persona.

### Mapping to BDI
- **Beliefs** ↔ memory/belief store  
- **Desires** ↔ goals/utility  
- **Intentions** ↔ selected **plans** (your DSL) running under the (async) runtime

---

## Minimal Agent Kernel (ENTITY) — Python Skeleton

```python
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable

# --- beliefs/memory ---
@dataclass
class BeliefBase:
    facts: Dict[str, Any] = field(default_factory=dict)       # long-term memory
    weights: Dict[str, float] = field(default_factory=dict)   # confidences

    def update(self, k: str, v: Any, w: float | None = None):
        self.facts[k] = v
        if w is not None:
            self.weights[k] = self.weights.get(k, 0.0) + w

# --- goals & intentions ---
@dataclass(frozen=True)
class Goal:
    name: str
    params: Dict[str, Any]

@dataclass(frozen=True)
class Intention:
    plan_ast: Any
    evaluator: Callable[[Dict[str, Any]], float] | None = None

# --- policy (how to pick intentions) ---
class Policy:
    def propose(self, goals: List[Goal], beliefs: BeliefBase) -> List[Intention]:
        # map goals+beliefs → candidate plans (ASTs)
        raise NotImplementedError

    def select(self, intents: List[Intention], ctx: Dict[str, Any]) -> Intention | None:
        # choose based on utility, budget, risk, deadlines
        return intents[0] if intents else None

# --- the Agent (ENTITY) ---
@dataclass
class AgentEntity:
    aid: str
    beliefs: BeliefBase
    goals: List[Goal]
    skills: Dict[str, Callable]           # registered task impls
    policy: Policy
    runtime: Any                          # your (async) compiler/executor
    inbox: asyncio.Queue
    bus: Any                              # pub/sub
    persist: Callable[[BeliefBase], None] # storage hook
    ctx: Dict[str, Any] = field(default_factory=dict)         # tools, budgets…

    async def perceive(self, msg: Any):
        # turn events into belief updates
        if isinstance(msg, dict) and "obs" in msg:
            self.beliefs.update("last_obs", msg["obs"], w=0.1)

    async def act_once(self):
        intents = self.policy.propose(self.goals, self.beliefs)
        choice = self.policy.select(intents, self.ctx)
        if not choice:
            return
        run = self.runtime.compile(self.skills, choice.plan_ast)  # reuses your DSL
        new_state = await run({"beliefs": self.beliefs.facts}, self.ctx)
        # fold result back into beliefs/memory
        self.beliefs.update("last_state", new_state, w=0.05)
        self.persist(self.beliefs)

    async def run(self):
        while True:
            msg = await self.inbox.get()
            if msg == "__STOP__":
                break
            await self.perceive(msg)
            await self.act_once()
```
**Notes**
- The **agent** owns goals, beliefs, mailbox, and persistence.  
- The **plan DSL** is the *intention executor*, not the definition of the agent.

---

## Integrating with the Existing Plan DSL

Your current DSL (sequence/parallel/choose/focus/loop) remains unchanged and becomes the **Intention Executor**. Example:

```python
# Pseudocode – depends on your actual names in agents/actions.py and runtime
from LambdaCat.agents.actions import Task, sequence, parallel, focus
from LambdaCat.agents.runtime_async import compile_plan  # new async version

# Define skills (tasks). They can be sync or async; compiler handles both.
async def parse_query(state, ctx=None):
    q = state["query"]; return {**state, "kws": q.split()}

async def http_search(state, ctx=None):
    http = ctx["http"]; kws = state["kws"]
    hits = await http.get("/search", params={"q": " ".join(kws)})
    return {**state, "web_hits": hits}

async def ask_llm(state, ctx=None):
    llm = ctx["llm"]; hits = state.get("web_hits", [])
    ans = await llm.complete(f"Synthesize from: {hits}")
    return {**state, "answer": ans}

skills = {
    "parse_query": parse_query,
    "http_search": http_search,
    "ask_llm": ask_llm,
}

plan = sequence(
    Task("parse_query"),
    Task("http_search"),
    Task("ask_llm"),
)

runtime = type("RT", (), {"compile": lambda self, impl, ast: compile_plan(impl, ast)})()
```

The **agent policy** chooses this `plan` as an **Intention**, passes it to the runtime, and integrates the result back into beliefs.

---

## Reactive Bus & Multi‑Agent Wiring (sketch)

```python
# Minimal in‑proc pub/sub bus
class Bus:
    def __init__(self):
        self.topics: dict[str, list[asyncio.Queue]] = {}

    async def subscribe(self, topic: str) -> asyncio.Queue:
        q = asyncio.Queue()
        self.topics.setdefault(topic, []).append(q)
        return q

    async def publish(self, topic: str, msg):
        for q in self.topics.get(topic, []):
            await q.put(msg)

async def run_system(agentA: AgentEntity, agentB: AgentEntity, bus: Bus):
    inboxA = await bus.subscribe("tasks")
    inboxB = await bus.subscribe("tasks")
    agentA.inbox = inboxA
    agentB.inbox = inboxB
    tA = asyncio.create_task(agentA.run())
    tB = asyncio.create_task(agentB.run())
    await bus.publish("tasks", {"obs": {"query": "graph transformers"}})
    await asyncio.sleep(1.5)
    await bus.publish("tasks", "__STOP__")
    await bus.publish("tasks", "__STOP__")
    await asyncio.gather(tA, tB)
```

---

## Beliefs, Goals, and Policy — Minimal Patterns

```python
# Belief update utility (weighted)
def update_belief(beliefs: BeliefBase, prop: str, delta_logit: float):
    w = beliefs.weights.get(prop, 0.0) + delta_logit
    beliefs.weights[prop] = w

# Goal → intentions mapper (toy)
class ResearchPolicy(Policy):
    def propose(self, goals, beliefs):
        intents = []
        for g in goals:
            if g.name == "answer_query":
                plan = plan_for_answering_query()   # build DSL AST
                intents.append(Intention(plan_ast=plan))
        return intents
```

---

## Persistence Hook (simple JSON)

```python
import json, os
from dataclasses import asdict

def persist_beliefs_json(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    def save(beliefs: BeliefBase):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"facts": beliefs.facts, "weights": beliefs.weights}, f, indent=2)
    return save
```

---

## Why this is now “Agents,” not just “Plans”

- **Entity & identity:** each agent has an `aid`, a mailbox, and persistent beliefs/goals.  
- **Temporal behavior:** agents **run** over time, perceive events, schedule intentions, and learn from outcomes.  
- **Autonomy:** goals + policy select intentions; plans are the *means*, not the *end*.  
- **Sociality:** bus/mailboxes enable multi-agent collaboration or competition.  
- **Memory & adaptation:** belief updates and persistence carry experience forward.

---

## Optional: Diagram

Use the monadic wiring diagram for the intention executor (Kleisli pipeline). Files generated earlier:

- PNG: `monadic_agents_diagram.png`  
- SVG: `monadic_agents_diagram.svg`  
- PDF: `monadic_agents_diagram.pdf`

(Place alongside this spec in the repo docs.)

---

## Minimal Checklist to Implement

1. **Agent kernel** (`AgentEntity`, `BeliefBase`, `Goal`, `Intention`, `Policy`).  
2. **Async runtime** (`compile_plan_async`) with real parallelism + timeouts.  
3. **Bus** (mailboxes/pub-sub) and a 2-agent demo.  
4. **Persistence** for beliefs/memory.  
5. **Examples**: research agent as entity; reactive loop with events.  

This keeps your categorical DSL intact and upgrades the system from *“execution plans”* to *“living agents.”*
