# ActionList — LambdaCat Deep Dive & Recommendations
**Date:** August 22, 2025

This file is the actionable extraction of the full LambdaCat audit I just ran, including an explicit, checkable task list and the full analysis below for context.

---

## ✅ TL;DR ActionList (checklist)

### P0 — Immediate (stabilize, fix correctness)
- [ ] **Wire real commutativity checks**: `core/diagram.py` → delegate to `ops_category.check_commutativity` (or add `check_commutativity_in(self, C, …)` and deprecate the old stub).
- [ ] **Remove duplicate** `compile_plan` **definition**: `agents/runtime.py` (keep single public entry point).
- [ ] **Delete no-op comprehensions/tuples** in `core/ops_category.py` (`opposite_category`, `slice_category`).
- [ ] **README/Manual parity**: remove or implement `normalize` (see minimal helper below). Make docs match current API.
- [ ] **Presentation.relations status**: document that relations are currently informational; add a law/assert helper now. (Plan rewrite/normal forms in P1.)
- [ ] **Error messages**: in `Cat.compose`/composition lookup, include both arrow names and endpoints in raised errors.
- [ ] **Agents docs clarity**: document `parallel/choose` with concrete examples; surface `choose_fn`/`aggregate_fn`.
- [ ] **License clarity**: clarify `LicenseRef-HNCL-1.0`; consider dual-license (HNCL + Apache-2.0 for core) or clearly scope non-commercial use.

### P1 — Next (1–2 sprints)
- [ ] **Export ergonomics**: re-export `standard` constructors in `core/__init__.py`.
- [ ] **Normalize helper**: ship `normalize(C, Formal1)`; add tests; reference in docs.
- [ ] **Relations → light rewriting**: orient relations and compute normal forms (terminating rewrite); expose `equal(p,q)` on `Formal1`.
- [ ] **CLI**: `lambdacat laws --suite category|functor|monad --json|text` and `lambdacat render --format mermaid|dot` with friendly errors.
- [ ] **CI refresh**: replace deprecated GitHub Actions `set-output` with `$GITHUB_OUTPUT`; keep 3.11/3.12 matrix (optionally add 3.10).

### P2 — Later (nice-to-have)
- [ ] **Hom-set helpers**: `hom(C,X,Y)`, `is_iso(C,f)`, `iso_classes(C)`.
- [ ] **Limits UX**: counterexample builders for failed products/equalizers to aid debugging/teaching.
- [ ] **Graphviz render_to_file(path)** helper that no-ops with a friendly message if extra is missing.
- [ ] **Docstring audit**: add `pydocstyle` to CI; improve narrative consistency.
- [ ] **Interop (HyperCat/SHE)**: thin adapters to round-trip categories/diagrams; rendering parity with Mermaid/DOT.

---

## 0) Executive Summary

**What’s strong**
- Solid **core 1-category model** with typed composition/identity checks and JSON IO.
- **Law suites** for categories, functors, naturality, applicative, monad (Hypothesis-based property tests).
- **Functional stack**: Option/Result/Reader/Writer/State/List/Either/Id; **Kleisli** category builder + registry.
- **Higher structure**: **limits** (products, equalizers) and **adjunctions** with triangle identities.
- **Optics**: Lens/Prism/Iso composition.
- **Agents DSL & runtime**: seq/parallel/choose/focus/loop_while; compile to functions/Kleisli.
- Rendering: **Mermaid** + **Graphviz**; CI includes tests, mypy, ruff; release pipeline prepped.

**Where it’s brittle**
- `Diagram.check_commutativity` is a **stub**; contradicts docs.
- Duplicate `compile_plan` in `agents/runtime.py`.
- Stray **no-op comprehensions** in `ops_category`.
- README mentions **`normalize`** that doesn’t exist.
- `Presentation.relations` unused for rewriting/closure.
- Law output not surfaced via CLI; counterexamples not obvious.
- **License** (HNCL) constrains adoption.

---

## 1) Confirmed Changes & Additions (high-level)
- Core: `Cat`, `Presentation`, builders; `to_json/from_json`.
- Ops: `opposite_category`, `slice_category`, path search, standalone commutativity checker, standard categories.
- FP: `FunctorT`, `ApplicativeT`, `MonadT`; instances; Kleisli builder + registry.
- Laws: suites + runner + `SuiteReport`.
- Higher structure: `limits.py` (products/equalizers), `adjunctions.py`.
- Optics: Lens/Prism/Iso.
- Agents: plan DSL + compilers (`compile_plan`, `compile_to_kleisli`), eval helpers.
- Renderers: Mermaid, Graphviz (extras guarded).
- Tooling: CI (pytest+coverage+mypy+ruff), release pipeline, docs Manual + notebooks.

---

## 2) Priority Fixes (P0)

1) **Real commutativity checks**
```diff
# core/diagram.py
@@
-    def check_commutativity(self, source: str, target: str, paths: Sequence[Sequence[str]]) -> CommutativityReport:
-        """Check commutativity of paths from source to target."""
-        return CommutativityReport(True, {}, None)
+    def check_commutativity(self, C: Cat, source: str, target: str,
+                            paths: Sequence[Sequence[str]]) -> CommutativityReport:
+        """Check that provided paths from `source` to `target` commute in category `C`."""
+        from .ops_category import check_commutativity
+        return check_commutativity(C, source, target, paths)
```
(*Non-breaking alternative: add `check_commutativity_in(self, C, …)` and deprecate the old signature.*)

2) **Remove duplicate `compile_plan`**
```diff
# agents/runtime.py
@@
-def compile_plan(...):
-    """Compile a plan to an executable function."""
-    return _compile_plan(...)
+# (remove earlier duplicate; keep single public entry point below)
```

3) **Strip no-op comprehensions**
```diff
# core/ops_category.py
@@ def opposite_category(C: Cat) -> Cat:
-    tuple((f"{a.name}^op", a.target, a.source) for a in C.arrows)
@@ def slice_category(...):
-    tuple(ArrowGen(name, src, tgt) for (name, src, tgt) in arrows_list)
+    # (construction happens below; remove unused tuple)
```

4) **README parity on `normalize`**  
Implement or remove mention. Minimal helper (optional P1) below.

5) **`Presentation.relations`**  
P0: document as informational; add assertion helper.  
P1: add oriented rewriting/normal forms.

6) **Error messages**  
Echo arrow names and endpoints for undefined or ill-typed compositions.

7) **Agents docs**  
Clarify `parallel/choose`; wire `aggregate_fn`/`choose_fn` examples.

8) **License**  
Clarify HNCL; consider dual-license for broader adoption.

---

## 3) Notable Bugs / Paper Cuts (P1)
- Re-export `standard` constructors for ergonomics.
- Avoid duplication of path logic between `Diagram` and `ops_category` (decide typed vs graph-only and document).
- Add examples covering Writer aggregation vs Result short-circuit in parallel/choose flows.
- Add `render_to_file(path)` safe helper for Graphviz.
- Modernize CI outputs; tighten mypy ignores gradually.

---

## 4) Short Roadmap

**Phase A — Stabilization**  
Fix commutativity, duplicate `compile_plan`, no-op comps; update README/Manual; add failing commutativity example; re-export `standard` constructors.

**Phase B — Relations & Normalization**  
Implement `normalize(Formal1, C)`; provide `equal(p,q)` using relations + composition; (optional) small terminating rewrite system.

**Phase C — Law UX & CLI**  
`lambdacat laws` with JSON/text reporters & witnesses; badges from CI artifacts.

**Phase D — Agents polish**  
Reference interpreters (sequential, applicative, monadic); law-checked examples with Writer/Result; `focus(lens,…)` demo.

**Phase E — Interop (HyperCat/SHE)**  
Adapters Cat/Diagram ↔ HyperCat; Mermaid/DOT parity.

---

## 5) Suggested Patches (ready-to-paste helpers)

### A) `core/diagram.py`: delegate to ops checker
```python
def check_commutativity(self, C: Cat, source: str, target: str, paths: Sequence[Sequence[str]]):
    from .ops_category import check_commutativity
    return check_commutativity(C, source, target, paths)
```

### B) `agents/runtime.py`: single `compile_plan`
*(Remove the earlier duplicate, keep the final public wrapper that calls `_compile_plan`.)*

### C) `core/ops_category.py`: remove no-op tuples
*(Delete the unused tuple comprehensions; construction occurs later in the functions.)*

### D) `core/builder.py`: minimal `normalize` (optional P1)
```python
from .presentation import Formal1

def normalize(C: Cat, path: Formal1) -> str:
    """Right-associate and fold a Formal1 to a single morphism name via C.compose."""
    if not path.factors:
        raise ValueError("empty path")
    acc = path.factors[0]
    for f in path.factors[1:]:
        acc = C.compose(f, acc)  # g∘f convention
    return acc
```

---

## 6) Testing & CI

Add targeted regression tests:
- **Commutativity failure**: triangle `A→B→C` vs `A→C` with `g∘f ≠ h`; assert mismatch and witness paths.
- **Opposite category**: verify `(g^op ∘ f^op) = (f ∘ g)^op` and identity mapping.
- **Slice category**: typing and identities; `id_X ∘ f = f` witness.
- **Normalize**: trivial path, associativity alignment, undefined composition failure.

CI:
- Replace `set-output` with `$GITHUB_OUTPUT`.
- Python 3.11/3.12 matrix (optionally 3.10 if needed).

---

## 7) Documentation Upgrades

- **Manual**: run a law suite on a purposely failing example with **human-readable witness** output.
- **Relations**: candid section on current status + assertion helper; roadmap to rewriting.
- **Agents**: two demos—(1) `Result` short-circuit vs (2) `Writer` aggregation under `parallel`; (3) `focus(lens,…)` on a small state.

---

## 8) Interop Notes (HyperCat/SHE)

- Thin adapters to and from HyperCat categories/diagrams; pass through objects, arrows `(name, src, tgt)`, identities, composition dict.
- Rendering parity between Mermaid/DOT outputs to enable cross-tool validation in PRs.

---

## 9) Nice-to-Haves (P2)

- Hom-set API; iso checks & iso class partitioning.
- Counterexample builder utilities for limits.
- Graphviz `render_to_file` helper.
- Docstring audit via `pydocstyle`.

---

## 10) Closing

LambdaCat is already a credible categorical FP core with agents. The P0 actions make commutativity checks real, remove duplication/no-ops, and bring docs to ground truth. P1 adds small but powerful rewriting/normalization and a CLI to expose law failures with witnesses. P2 rounds out UX and interop.
