# LambdaCat — ActionList for Basic 1-Category Support

Owner: **Kishore**
Reviewer: **Mirco**
Status: **Draft v1.0**

Goal: Bring LambdaCat to a **minimally complete 1-category toolkit** suitable for category-theory demos, teaching, and light research.

---

## Phase 0 — Repo Hygiene (Prereq)
- [ ] **Unify naming** (`walking_isomorphism` everywhere; remove `walking_iso` mentions).
- [ ] **Public API surface** (`lambdacat.core`, `lambdacat.functors`, `lambdacat.monads`, `lambdacat.diagrams`).
- [ ] **Docs runner**: all code blocks in docs are executable (doctest or CI snippet check).
- [ ] **pyproject** metadata + `python = ">=3.11"`; add CHANGELOG, versioning policy.

---

## Phase 1 — Core 1-Category Model

### 1. Objects & Morphisms
- [ ] `Object`: keep as string/Hashable alias (document this).
- [ ] `Morphism` dataclass:
  - fields: `name: str`, `dom: Object`, `cod: Object`.
  - `__repr__` and stable equality by name.
- [ ] `identity(A) -> Morphism` factory; ensure one per object.

**Acceptance:** constructing morphisms records `dom/cod` consistently; `identity(A).dom == identity(A).cod == A`.

### 2. Category Structure
- [ ] `Cat`:
  - fields: `objects: set[Object]`, `arrows: dict[str, Morphism]`,
    `hom: dict[tuple[Object,Object], list[str]]` (names), `composition: dict[tuple[str,str], str]`,
    `identities: dict[Object, str]`.
  - method: `compose(f: str, g: str) -> str` returning composite name.
- [ ] **Typed composition guard**:
  - refuse `(f,g)` when `cod(f) != dom(g)` with a clear error.

**Acceptance:** trying to compose ill-typed arrows raises `TypeError` with `cod(f)`/`dom(g)` details.

### 3. Law Suite (Category)
- [ ] `_IdentitiesLaw`: `id ∘ f = f = f ∘ id` for all composable pairs.
- [ ] `_AssociativityLaw`: `(h∘g)∘f == h∘(g∘f)` for all typed triples.
- [ ] `_WellTypedComposition`: 
  - if `cod(f)==dom(g)` then `(f,g)` **must** be in `composition`;
  - every `(f,g)->h` must satisfy `dom(h)=dom(f)`, `cod(h)=cod(g)`.
- [ ] CLI/pytest output style:
  - pass: `[✓] <law>`
  - fail: `[✗] <law>: <why> {context...}`

**Acceptance:** `pytest -k category_laws -q` shows green on good cats; shows human-readable diagnostics on broken ones.

---

## Phase 2 — Diagrams & Commutativity

### 4. Diagram Representation
- [ ] `Diagram` struct: `objects`, `edges: list[tuple[str,str,str]]` (src, tgt, arrow-name).
- [ ] `paths(A,B) -> list[list[str]]` up to a bound (to avoid blowup).

### 5. Commutativity Checker
- [ ] `check_commutativity(C: Cat, A: Object, B: Object, paths: list[list[str]]) -> bool | Report`.
- [ ] Error report enumerates path composites and mismatches.

### 6. Rendering
- [ ] `render.mermaid(diagram | cat_subset) -> str`.
- [ ] Optional: `render.graphviz(...)` if `graphviz` installed.

**Acceptance:** triangle example (`g∘f = h`) renders and checks; mismatch produces diff of composites.

---

## Phase 3 — Standard Categories Library

### 7. Stock Cats (tiny, explicit)
- [ ] `discrete_category(X: Iterable[Object])`.
- [ ] `monoid_category(M: set, op, e)` (one-object category).
- [ ] `poset_category(P: set, leq)` (arrow iff `x ≤ y`).
- [ ] `delta_category(n)` (Δⁿ).

**Acceptance:** each passes CATEGORY_SUITE and ships with a doctested example.

---

## Phase 4 — Functors & Naturality

### 8. Functors
- [ ] `FunctorBuilder(C, D)`:
  - `add_object_mapping(A, F_A)`; `add_morphism_mapping(f, F_f)`.
  - build enforces: `F(id_A) = id_{F(A)}`, `F(g∘f) = F(g)∘F(f)`.
- [ ] `FUNCTOR_SUITE` laws: identity & composition preservation with explicit failure diffs.

### 9. Natural Transformations
- [ ] `NaturalTransformation(F, G, components: dict[Object, str])` (names of D-arrows).
- [ ] `check_naturality(C, D, F, G, eta)`:
  - verify `eta_Y ∘ F(f) == G(f) ∘ eta_X` for all `f: X→Y`.
  - report lists failing squares with computed composites.

**Acceptance:** identity NT passes; a purposely broken component shows exact offending square.

---

## Phase 5 — Utilities & Docs

### 10. Opposite / Slices
- [ ] `C.op()` producing `C^op`.
- [ ] (Optional) `slice(C, A)` with induced hom-sets.

### 11. Pretty & I/O
- [ ] Pretty `repr` for `Cat`, `Morphism`, `Functor`, `Natural`.
- [ ] `to_json`/`from_json` for small cats.

### 12. Docs & Examples
- [ ] **Manual** section “What can I do with a category?” with:
  - diagram draw, commutativity check, laws run, functor build, NT check.
- [ ] **Law outputs** included verbatim (pass & fail examples).
- [ ] **Cookbook**: triangle commutes; square that fails; poset-as-category; monoid-as-category.

**Acceptance:** `docs/` builds; doctests pass in CI.

---

## Phase 6 — CI & Tests

- [ ] `pytest -k laws -q` target aggregating all law suites.
- [ ] Hypothesis-based sampling for associativity on generated small cats (optional bound).
- [ ] CI badge for “laws passed: <n>/<N>” printed in logs.

---

## Stretch (Post v0.1)

- [ ] Limits in finite cats: products, equalizers (very small sizes).
- [ ] Adjunction skeleton: show one toy adjunction with law checks.
- [ ] Kleisli category builder for any registered monad instance.

---

## Milestones & Review

- **M1 (Core):** Phases 1–3 done → “Basic 1-Categories” tag.  
- **M2 (Structure):** Phase 4 + 5 → “Functors & Naturality”.  
- **M3 (Polish):** Phase 6 + stretch picks.

Each milestone should include: passing CI, updated docs, and one new tutorial notebook.

---

## Acceptance Checklist (Overall)
- [ ] Can define a small category with typed arrows and total composition on typed pairs.
- [ ] Running `CATEGORY_SUITE` prints ✓ outputs; broken cats produce meaningful ✗ reports.
- [ ] Can draw a diagram and verify commutativity.
- [ ] Have `discrete`, `monoid`, `poset`, `delta` categories out of the box.
- [ ] Can define a functor and check its laws.
- [ ] Can define a natural transformation and see failing squares if wrong.
- [ ] Manual contains concrete code + outputs mirroring the above.

