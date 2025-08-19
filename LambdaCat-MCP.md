# LambdaCat — Minimal-Complete Product (MCP)

Owner: **Kishore**
Reviewer: **Mirco**
Status: **Draft v1.0**

Goal: Turn LambdaCat from a useful skeleton into a **small-but-complete** FP + 1-category toolkit, without overlapping HyperCat.

---

## A. Clear Scope

LambdaCat is for:
- **Finite 1-categories**: build, inspect, render, check.
- **FP stack**: Functor → Applicative → Monad (+ laws).
- **Kleisli** categories for agents.
- **Optics** for immutable state work.
- **Diagrammer** with commutativity checks.
- **Bridges** to HyperCat for higher-category/heavy theory.

Out of scope: higher categories, homotopy, general proof search, full limits/colimits beyond tiny cases.

---

## B. Required Modules & APIs

### 1) Core 1-Category
- `Cat`: objects, morphisms (`dom/cod`), total `composition`, `identities`.
- `compose(f,g)` guards: only when `cod(f) = dom(g)`; great error messages.
- **Law Suite**: identities, associativity, well-typed composition.
- **Standard cats**: `discrete(X)`, `monoid(M,op,e)`, `poset(P,≤)`, `delta(n)`.
- **Utils**: `op()`, optional `slice(C,A)`, `to_json/from_json`.

### 2) Diagrams & Commutativity
- `Diagram(objects, edges=[(A,B,"f"), ...])`.
- `check_commutativity(C, A, B, paths)` → bool | report (with path composites and diffs).
- Renderers: `render.mermaid`, optional `render.graphviz`.

### 3) Functors & Naturality
- `FunctorBuilder(C,D)` enforces `F(id)=id`, `F(g∘f)=F(g)∘F(f)`.
- `FUNCTOR_SUITE` with diff-y failure output.
- `NaturalTransformation(F,G, components)` + `check_naturality(...)` (shows failing squares).

### 4) FP Stack (Usable, Law-Checked)
- **Data**: `Option`, `Result`, `NonEmptyList`.
- **Algebra**: `Semigroup`, `Monoid` (+ laws).
- **Typeclasses**: `Functor`, `Applicative`, `Monad` protocols.
- **Instances**: `Id`, `Option`, `Result`, `Reader`, `Writer`, `State`, `List`.
- **Law suites**: Functor / Applicative / Monad (property-based where sensible).
- **Kleisli**: `kleisli_cat(M, Obj)` and `Kleisli.then`, `Kleisli.id`.

### 5) Agents (Small but Real)
- Plan DSL: `Primitive`, `Sequence`, `Choose`, `LoopWhile`, lawful `Parallel` via Applicative `zip`.
- Compiler: `compile(plan, monad=State, mode="monadic"|"applicative") → Kleisli`.
- Examples: counters (State), logs (Writer), fail-fast (Result).

### 6) Optics (DX Payoff)
- `Lens`, `Prism`, `Iso` with `get/set/modify` and optic laws.
- `Focus(lens, subplan)` to act on nested state immutably.

---

## C. Developer Experience

- Readable law outputs (✓/✗ with context), not stack traces.
- `pytest -k laws` target; “laws passed: m/n” summary.
- Doctested docs; every code block runs.
- Stable public surface: `lambdacat.core`, `.functors`, `.monads`, `.optics`, `.diagrams`, `.render`, `.agents`, `.data`, `.control`.

---

## D. Teaching-First Docs

- **What can I do with a category?** explore, render, chase diagrams, run laws, build functors, check naturality (with real outputs).
- **From Functors to Monads**: lineage + laws + one type shown as Functor → Applicative → Monad.
- **Cookbook (10 runnable snippets)**: Writer logging; Reader config; Result validation (Applicative vs Monad); State counters; List search; Lenses on nested dict; Commuting triangle; Failing square; Plan→Kleisli agent; Applicative parallel plan.

---

## E. Interop with HyperCat

- Export small `Cat`/diagram fragments to HyperCat for deep checks.
- Optional: call HyperCat’s checker if installed; otherwise use LambdaCat’s fast one.

---

## F. Acceptance Criteria

- Define a tiny category, prove laws, render it, chase equalities, build a functor, check naturality — all with runnable code and visible outputs.
- FP side: map/ap/bind work on core types; law suites green; Kleisli category composes agents; optics laws hold.

---

## Milestones

- **M1 (Core):** 1) Core category + laws + std cats 2) Diagrams + commutativity + rendering.  
- **M2 (Structure):** 3) Functors + naturality 4) FP stack + Kleisli.  
- **M3 (Polish):** 5) Agents, 6) Optics, Docs, DX polish.
