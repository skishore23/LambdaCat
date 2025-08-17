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

Run tests locally:

```bash
pytest -q
```
