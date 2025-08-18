# Multi‑stage Research & Citation Agent (with Consistency Checks)

Composable agents on a typed categorical core: objects, functors, naturality, and runtime law checks.

## Summary

A production‑ready research agent that searches, fetches, extracts, cross‑checks, cites, and drafts. It is built as a composable plan over pure actions with:
- Explicit sequencing, parallelism, branching, lenses, and loops
- Executable checks for structural correctness (category/functor/naturality suites)
- Deterministic orchestration and full provenance/tracing
- Optional LLM components for extraction and drafting

## Why this approach

- Clarity and control: plans are data (immutable), actions are pure functions, interpreters are deterministic.
- Verifiability: run executable law checks in CI (category/functor/naturality) on the small categories that model adapters and transforms.
- Composability: `sequence`, `parallel`, `choose`, `focus` (lenses), `loop_while` let you scale without hidden control flow.
- Auditability: every run yields per‑step timings and optional snapshots; generate Mermaid diagrams for categories, functors, plans, and execution Gantt.

### How it compares to popular agent frameworks

- LangGraph / LangChain: excellent orchestration; LambdaCat adds a typed categorical core and executable law checks for internal transforms.
- AutoGen: powerful multi‑agent conversations; LambdaCat focuses on deterministic compositional plans with explicit aggregators/choosers.
- CrewAI: easy role‑based composition; LambdaCat emphasizes verifiable structure (laws) and immutable plan data structures.
- LlamaIndex: great retrieval tooling; LambdaCat integrates such tools as pure actions inside a law‑checked runtime.

The difference: we treat the agent as a small category presentation and use functors to interpret plans into actual code, with checks you can run.

---

## Problem scope

Build a literature‑grade research agent that:
- Normalizes queries, searches multiple engines, and fetches sources
- Extracts salient facts/claims with citations
- Cross‑checks claims across sources and flags conflicts
- Summarizes into a draft with embedded citations and a bibliography
- Produces a clear, auditable trace and diagrams

---

## Category‑theoretic model

- Objects (data shapes): `Query`, `URL`, `HTML`, `Text`, `Facts`, `Claims`, `Citations`, `Draft`.
- Morphisms (actions): pure transforms between shapes, e.g., `search: Query → URL*`, `fetch: URL → HTML`, `extract: Text → Facts`.
- Functor: plan algebra (`Formal1`) → concrete runtime `(State, Ctx?) → State` via `strong_monoidal_functor`.
- Naturality idea: different extraction pipelines should commute with a canonicalization map (consistency across adapters).

You can model adapter invariants with small categories and run suites (`CATEGORY_SUITE`, `FUNCTOR_SUITE`) and `check_naturality` where appropriate.

---

## State model

Use a single immutable state with lenses to operate on substructures.

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class ResearchState:
    query: str
    urls: List[str]
    docs: List[str]
    extractions: List[dict]  # canonical claim records {claim:str, evidence:str, source:str}
    claims: List[dict]       # reconciled claims with support/contradiction counts
    draft: Optional[str]
```

---

## Actions (pure)

- normalize_query: `ResearchState → ResearchState`
- search_duckduckgo / search_serp: `ResearchState → ResearchState`
- fetch_next: `ResearchState → ResearchState` (looped until URLs exhausted)
- extract_v1 / extract_v2: `ResearchState → ResearchState` (LLM or rules)
- reconcile_claims: `ResearchState → ResearchState` (aggregate support/contradictions)
- cite_and_format: `ResearchState → ResearchState`
- draft_summary: `ResearchState → ResearchState` (LLM optional)
- score_quality: `ResearchState → ResearchState` (attach metrics)

All actions are written as pure functions `(state, ctx?) -> state` so they are easy to test.

---

## Plan algebra (structure)

- Stage 1: Normalize and search
- Stage 2: Fetch all URLs (loop)
- Stage 3: Parallel extraction (heterogeneous extractors)
- Stage 4: Reconcile and cross‑check
- Stage 5: Draft with citations and score

```python
from LambdaCat.agents import task, sequence, parallel, loop_while, focus, lens

plan = sequence(
  task("normalize_query"),
  task("search_duckduckgo"),
  loop_while(lambda s: len(s.urls) > 0, task("fetch_next")),
  parallel(task("extract_v1"), task("extract_v2")),  # aggregator at run-time
  task("reconcile_claims"),
  task("cite_and_format"),
  task("draft_summary"),
  task("score_quality"),
)
```

At run‑time you must provide an `aggregate_fn` to combine parallel outputs (e.g., merge extraction lists deterministically).

---

## Consistency checks

- Extraction commutativity (natura­lity‑style): for adapter `A` and canonicalizer `K`, check `K ∘ A(f) == A'(K ∘ f)` on a sample set of transforms where meaningful.
- Category laws for adapter categories: run `CATEGORY_SUITE` on small categories modeling your transform tables.
- Functor preservation: if you formalize a mapping of adapter arrows to canonical arrows, run `FUNCTOR_SUITE`.
- Citation grounding: each claim must reference at least one source snippet; enforce at reconciliation time.

These are executable checks you can run in tests/CI to prevent regressions.

---

## LLM integration points

- extract_v1/extract_v2: prompt to extract claims with inline citations (offsets or quote spans)
- draft_summary: prompt to write a concise literature summary with numbered references
- Optional: LLM ranking to select best extraction branch if multiple exist (plug into `choose` plans)

Keep the LLMs at the edges; core transforms remain small and testable.

---

## Provenance and diagrams

- Every run yields a trace with per‑step timings and optional snapshots.
- Use `LambdaCat.extras.viz_mermaid` to render:
  - Category/functor diagrams for small adapter models
  - Plan graphs and execution Gantt charts

```python
from LambdaCat.extras.viz_mermaid import plan_mermaid, exec_gantt_mermaid
print(plan_mermaid(plan_formal))
print(exec_gantt_mermaid(report))
```

---

## Evaluation (metrics)

- Coverage: number of unique sources fetched and used
- Grounding: claims with at least one citation (%), contradictions flagged
- Consistency: agreement between extractors (Jaccard over normalized claim sets)
- Quality: summary readability/length, citation correctness (spot‑checks)
- Latency & cost: per‑stage timings, token usage

---

## Why LambdaCat vs existing OSS agents

- Typed categorical core: model small adapter categories explicitly; avoid implicit, ad‑hoc wiring.
- Executable law checks: run suites for identities/associativity, functor preservation, and naturality‑style consistency on sample sets.
- Deterministic orchestration: explicit aggregators and choosers; no hidden event loops.
- Lens‑based state focus: operate on substructures without side effects.
- Diagram‑ready: auto‑generate Mermaid diagrams for plans and traces.

This yields agents that are easier to test, reason about, and audit.

---

## Implementation roadmap

1) Foundations
- Implement pure actions: normalize_query, search_duckduckgo, fetch_next, extract_v1 (LLM), extract_v2 (rules), reconcile_claims, cite_and_format, draft_summary, score_quality.
- Compose the plan with `sequence`/`parallel`/`loop_while`; provide an `aggregate_fn` for parallel extracts.
- Wire a minimal runner via `run_structured_plan` with `snapshot=True`.

2) Consistency & law checks
- Build tiny adapter categories and run `CATEGORY_SUITE` and `FUNCTOR_SUITE`.
- Add targeted `check_naturality` where APIs are compatible (same source/target functors).

3) Provenance and docs
- Emit execution traces; render plan and Gantt diagrams; commit diagrams under `docs/diagrams`.
- Add CI job to run suites and property tests (Hypothesis where helpful).

4) Extensions
- Add `choose` branches (e.g., heuristic vs LLM extraction) with an evaluator to select best.
- Add additional search providers and HTML parsers as swappable adapters.

---

## Minimal code sketch

```python
from LambdaCat.agents import run_structured_plan

impl = {
  'normalize_query': normalize_query,
  'search_duckduckgo': search_duckduckgo,
  'fetch_next': fetch_next,
  'extract_v1': extract_v1,
  'extract_v2': extract_v2,
  'reconcile_claims': reconcile_claims,
  'cite_and_format': cite_and_format,
  'draft_summary': draft_summary,
  'score_quality': score_quality,
}

report = run_structured_plan(
  plan,
  impl,
  input_value=initial_state,
  aggregate_fn=lambda outs: outs[0] if len(outs)==1 else merge_extractions(outs),
  snapshot=True,
)
```

All referenced APIs exist in this repository: plan builders (`task`, `sequence`, `parallel`, `loop_while`, `focus`, `lens`), the structured runner, the law suites (`CATEGORY_SUITE`, `FUNCTOR_SUITE`), and Mermaid helpers.

