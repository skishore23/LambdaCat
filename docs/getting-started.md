# Getting Started

Install (core only):

```bash
pip install LambdaCat
```

Agents quickstart:

```python
from LambdaCat.core.presentation import Formal1
from LambdaCat.agents.eval import Agent

actions = {
  'denoise': lambda s, ctx=None: s.replace('~',''),
  'edges':   lambda s, ctx=None: ''.join(ch for ch in s if ch.isalpha()),
  'segment': lambda s, ctx=None: s.upper(),
  'merge':   lambda s, ctx=None: f"[{s}]",
}

agent = Agent(implementation=actions, evaluator=lambda out: len(out))
plan = Formal1(('denoise','edges','segment','merge'))
print(agent.run(plan, "~a~b_c-1").output)
```

Core minimal usage:

```python
from LambdaCat.core.presentation import Obj, ArrowGen, Presentation

A, B = Obj("A"), Obj("B")
f = ArrowGen("f", "A", "B")
p = Presentation((A,B), (f,))
```

## Hello Δ³ (simplex) tutorial

Build Δ³, a small category with objects 0..3 and unique arrows i→j for i≤j. Verify laws, define a functor, a natural transformation, and render diagrams.

```python
from LambdaCat.core.standard import simplex, walking_isomorphism, terminal_category, discrete
from LambdaCat.core.functor import FunctorBuilder
from LambdaCat.core.natural import Natural, check_naturality
from LambdaCat.core.laws import run_suite
from LambdaCat.core.laws_category import CATEGORY_SUITE
from LambdaCat.core import NATURAL_SUITE
from LambdaCat.extras.viz_mermaid import render_all, TwoCellView

# 1) Build categories
Delta3 = simplex(3)           # Objects: 0,1,2,3; arrows: id and i->j
Iso    = walking_isomorphism()

# 2) Check category laws
assert run_suite(Delta3, CATEGORY_SUITE).ok

# 3) Define a functor F: Δ³ → Iso
F = (FunctorBuilder('F', source=Delta3, target=Iso)
     .on_objects({"0":"A","1":"A","2":"B","3":"B"})
     .on_morphisms({"0->1":"id:A","1->2":"f","2->3":"id:B","0->3":"f"})
     .build())

# 4) Natural transformation η: F ⇒ F (identity components)
eta = Natural(source=F, target=F, components={"0":"id:A","1":"id:A","2":"id:B","3":"id:B"})
check_naturality(eta)
assert run_suite(eta, NATURAL_SUITE).ok

# 5) Render diagrams
md_map = render_all({
  'Delta3': Delta3,
  'Iso': Iso,
  'F': F,
  'eta': eta,
}, out_dir='docs/diagrams')

print("Wrote:", sorted(md_map.keys()))
```

Run tests locally:

```bash
pytest -q
```
