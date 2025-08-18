# LambdaCat — Functional Core for Applied Category Theory

> Composable agents on a typed categorical core: objects, functors, naturality, and runtime law checks.

---

## TL;DR

* **Core:** immutable `Obj`, `Cat`, explicit `composition` and `identities`, builder helpers, law suites.
* **Plugins:** stubs only (e.g., Tamari placeholder); no features are enabled by default.
* **Agents:** plans as formal words → mapped to real Python callables by a sequential functor; structured plans via explicit interpreter; scoring + traces.
* **Laws:** extensible law engine → suites for categories; proofs helpers for universal properties.
* **Viz:** automatic **Mermaid** exporters for categories, functors, naturality squares, plans, and execution Gantt.
* **Packaging:** pip-installable core.

---

## Why LambdaCat?

- Confidence by construction: executable law checks for categories, functors, and naturality you can run in tests/CI.
- Composability that scales: a sequential functor interprets `Formal1` pipelines; structured plans via interpreter; build with `sequence`, `parallel`, `choose`, `focus`, and `loop_while`.
- Small, typed surface: minimal dataclasses and explicit maps; easy to read, reason about, and extend.
- Traceable runs: per‑step timings and optional snapshots for debugging and auditing.
- Diagram‑ready: generate Mermaid graphs for categories, functors, naturality squares, plans, and execution Gantt.
- Zero heavy deps by default: core stays lean; extras/plugins are opt‑in.

---

## Install

Core only (no heavy deps):

```bash
pip install LambdaCat
```

---

## Core Concepts & API

### Objects, Morphisms, Category

* **Objects**: immutable `Obj(name, data=None)`
* **Arrows (generators)**: immutable `ArrowGen(name, source, target)`
* **Category**: immutable `Cat(objects, arrows, composition, identities)`
* **Compose**: `Cat.compose(g, f)` keyed as `(g,f) ↦ g∘f`
* **Law check**: `run_suite(C, CATEGORY_SUITE)`

### Builder (tiny categories)

```python
from LambdaCat.core.builder import obj, arrow, build_presentation
A = obj("A"); B = obj("B"); f = arrow("f","A","B")
p = build_presentation((A,B),(f,))
```

### Path Ops (syntax-level)

- `identity(obj_name)` → `Formal1(('id:<Obj>',))`
- `compose(*paths)` → concatenated `Formal1`
- `normalize(path)`

### Functors

Map objects and morphisms, preserving identities and composition:

```python
from LambdaCat.core.functor import FunctorBuilder
F = (FunctorBuilder("F", source=C, target=C2)
     .on_objects({"A":"X","B":"Y"})
     .on_morphisms({"f":"φ"})
     .build())
```

### Natural Transformations

Components `η_X : F(X) → G(X)` satisfying naturality squares:

```python
from LambdaCat.core.natural import Natural, check_naturality
eta = Natural(source=F, target=G, components={"A": "id:A", "B": "id:B"})
check_naturality(eta)
```

---

## Extensible Law Engine (Proof-Friendly)

* `Law`, `LawSuite`, `Violation`, `SuiteReport`
* Provided suites:
  * `CATEGORY_SUITE` (identities + associativity)
  * `FUNCTOR_SUITE` (identities + composition)

```python
from LambdaCat.core.laws import run_suite
from LambdaCat.core.laws_category import CATEGORY_SUITE
from LambdaCat.core.laws_functor import FUNCTOR_SUITE
from LambdaCat.core import NATURAL_SUITE
assert run_suite(C, CATEGORY_SUITE).ok
assert run_suite(F, FUNCTOR_SUITE).ok
# Given eta: Natural(F,G), verify naturality suite
# from LambdaCat.core.natural import Natural
# eta = Natural(source=F, target=F, components={...})
# assert run_suite(eta, NATURAL_SUITE).ok
```

---

## Standard Categories

Helpers for common small categories:

```python
from LambdaCat.core.standard import terminal_category, discrete, simplex, walking_isomorphism
Term  = terminal_category()
Disc  = discrete(["A","B","C"])
Delta = simplex(3)
Iso   = walking_isomorphism()
```

### Category ops

```python
from LambdaCat.core.ops_category import opposite_category
Cop = opposite_category(Delta)
```

---

## Agents (Applied Category Theory)

### Plans as Formal Words

```python
from LambdaCat.core.presentation import Formal1
plan = Formal1(("denoise","edges","segment","merge"))
```

### Strong Monoidal Runtime

Maps plan → pipeline; runs functions with `(x)` or `(x, ctx)` signature.

```python
from LambdaCat.agents.runtime import sequential_functor
F = sequential_functor(impl)
out = F(plan)("a..b", ctx={})
```

### Agent Wrapper

Runner + scorer, plus `choose_best` across candidate plans.

```python
from LambdaCat.agents.eval import Agent
agent = Agent(implementation=impl, evaluator=lambda out: quality(out))
best_plan, report = agent.choose_best([plan1, plan2], data)
```

---

## Mermaid Diagrams (Automated)

We emit **Markdown strings** with Mermaid fences for all concepts; you just **paste** them into docs/PRs.

### Generating diagrams (step-by-step)

```python
from LambdaCat.core.standard import simplex, walking_isomorphism, terminal_category, discrete
from LambdaCat.core.functor import FunctorBuilder
from LambdaCat.core.natural import Natural
from LambdaCat.core.presentation import Formal1
from LambdaCat.extras.viz_mermaid import render_all, TwoCellView

Delta3 = simplex(3)
Iso    = walking_isomorphism()
Term   = terminal_category()
DiscAB = discrete(["A","B"]) 

F = (FunctorBuilder('F', source=Delta3, target=Iso)
     .on_objects({"0":"A","1":"A","2":"B","3":"B"})
     .on_morphisms({"0->1":"id:A","1->2":"f","2->3":"id:B","0->3":"f"})
     .build())
eta = Natural(source=F, target=F, components={"0":"id:A","1":"id:A","2":"id:B","3":"id:B"})
plan = Formal1(('denoise','edges','segment','merge'))
alpha = TwoCellView('α','X','Y','f','g')

md_map = render_all({
  'Delta3': Delta3,
  'Iso': Iso,
  'Terminal': Term,
  'DiscreteAB': DiscAB,
  'F': F,
  'eta': eta,
  'Plan': plan,
  'alpha': alpha,
}, out_dir='docs/diagrams')  # omit out_dir to just get strings back
```

Outputs are Markdown files under `docs/diagrams/*.md` with fenced ```mermaid blocks.

### Sample Mermaid Blocks

**Category**

```mermaid
graph LR
  A -- "f" --> B
  B -- "g" --> C
  A -- "h" --> C
```

**Functor**

```mermaid
graph LR
  subgraph Source
    S_A -- "f" --> S_B
  end
  subgraph Target
    T_X -- "φ" --> T_Y
  end
  S_A -.-> T_X:::map
  S_B -.-> T_Y:::map
classDef map stroke-dasharray: 3 3;
```

**Naturality**

```mermaid
graph LR
  FX["F X"] -->|F·f| FY["F Y"]
  FX -->|η X| GX["G X"]
  FY -->|η Y| GY["G Y"]
  GX -->|G·f| GY
```

**Plan**

```mermaid
graph LR
  in["⟦input⟧"] --> s1["denoise"]
  s1 --> s2["edges"]
  s2 --> s3["segment"]
  s3 --> s4["merge"]
  s4 --> out["⟦output⟧"]
```

**Execution Gantt**

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryTextColor': '#111111', 'textColor': '#111111', 'lineColor': '#111111', 'ganttAxisTextColor': '#111111', 'ganttSectionBkgColor': '#f8fafc', 'ganttSectionBkgColor2': '#ffffff', 'ganttSectionBkgOpacity': 1, 'ganttTaskLineColor': '#111111', 'ganttTaskTextColor': '#111111', 'sectionTextColor': '#111111' }}}%%
gantt
  dateFormat X
  axisFormat %L
  section steps
  denoise  :done, step1, 0, 12
  edges    :done, step2, 12, 24
  segment  :done, step3, 24, 55
  merge    :done, step4, 55, 78
```

---

## Mathematical Confidence (Proof-like Checks)

- Category axioms, functor laws, naturality, universal properties
- Property/meta-morphic tests for robustness

---
 
