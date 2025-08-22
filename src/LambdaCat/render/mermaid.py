"""Mermaid rendering for LambdaCat structures."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


def _fence(body: str) -> str:
    return "```mermaid\n" + body.strip() + "\n```"


# ---------------------- Category / Functor / Natural ----------------------

class _ArrowLike(Protocol):
    source: Any
    target: Any
    name: Any


class _CategoryLike(Protocol):
    arrows: Iterable[_ArrowLike]


def _iter_arrows(category: Any) -> Iterable[_ArrowLike]:
    # Support our core Cat (.arrows of ArrowGen) and any foreign shape with .morphisms
    if hasattr(category, "arrows"):
        return category.arrows  # type: ignore[return-value]
    if hasattr(category, "morphisms"):
        return category.morphisms  # type: ignore[return-value]
    return ()


def _obj_name(x: Any) -> str:
    return x.name if hasattr(x, "name") else str(x)


def _src_name(arrow: _ArrowLike) -> str:
    s = getattr(arrow, "source", "")
    return _obj_name(s)


def _tgt_name(arrow: _ArrowLike) -> str:
    t = getattr(arrow, "target", "")
    return _obj_name(t)


def _arr_name(arrow: _ArrowLike) -> str:
    return _obj_name(getattr(arrow, "name", arrow))


def category_mermaid(C: _CategoryLike | Any, *, hide_id: bool = True) -> str:
    lines: list[str] = ["graph LR"]
    arrows = sorted(_iter_arrows(C), key=lambda a: _arr_name(a))
    for a in arrows:
        name = _arr_name(a)
        if hide_id and _src_name(a) == _tgt_name(a) and (name.startswith("id:") or name.startswith("id_")):
            continue
        lines.append(f'  {_src_name(a)} -- "{name}" --> {_tgt_name(a)}')
    return _fence("\n".join(lines))


def diagram_mermaid(D: Any) -> str:
    lines: list[str] = ["graph LR"]
    for (s, t, name) in getattr(D, "edges", ()):  # type: ignore[attr-defined]
        lines.append(f'  {s} -- "{name}" --> {t}')
    return _fence("\n".join(lines))


def functor_mermaid(F: Any) -> str:
    S, T = F.source, F.target
    # Prefix node ids to avoid clashes across subgraphs
    def nid(prefix: str, name: str) -> str:
        return f"{prefix}_{name}"

    src = ["subgraph Source"]
    for a in sorted(_iter_arrows(S), key=lambda x: _arr_name(x)):
        src.append(f'  {nid("S", _src_name(a))} -- "{_arr_name(a)}" --> {nid("S", _tgt_name(a))}')
    src.append("end")

    tgt = ["subgraph Target"]
    for a in sorted(_iter_arrows(T), key=lambda x: _arr_name(x)):
        tgt.append(f'  {nid("T", _src_name(a))} -- "{_arr_name(a)}" --> {nid("T", _tgt_name(a))}')
    tgt.append("end")

    # Object map: Mapping[str,str] for CatFunctor
    links: list[str] = []
    if hasattr(F, "object_map") and isinstance(F.object_map, dict):
        for s_name, t_name in sorted(F.object_map.items(), key=lambda kv: kv[0]):
            links.append(f'  {nid("S", s_name)} -.-> {nid("T", t_name)}:::map')

    body = "\n".join(["graph LR", *src, *tgt, *links, "classDef map stroke-dasharray: 3 3;"])
    return _fence(body)


def naturality_mermaid(eta: Any, f: _ArrowLike) -> str:
    # Expect 'f' as an arrow-like object with .source/.target names
    X = _src_name(f)
    Y = _tgt_name(f)
    # Avoid problematic punctuation in edge labels: use 'F·f' style
    body = f"""
graph LR
  FX["F {X}"] -->|F·{_arr_name(f)}| FY["F {Y}"]
  FX -->|η {X}| GX["G {X}"]
  FY -->|η {Y}| GY["G {Y}"]
  GX -->|G·{_arr_name(f)}| GY
""".strip()
    return _fence(body)


# ------------------------------ Agents visuals ------------------------------

def plan_mermaid(plan: Any) -> str:
    factors: Sequence[str] = getattr(plan, "factors", ())
    nodes = ["in"] + [f"s{i}" for i in range(1, len(factors) + 1)] + ["out"]
    labels = ["⟦input⟧"] + list(factors) + ["⟦output⟧"]
    lines = ["graph LR"]
    for n, label in zip(nodes, labels):
        lines.append(f'  {n}["{label}"]')
    for i in range(len(nodes) - 1):
        lines.append(f"  {nodes[i]} --> {nodes[i+1]}")
    return _fence("\n".join(lines))


class _StepLike(Protocol):
    name: str
    ok: bool
    duration_ms: float


def exec_gantt_mermaid(report_or_trace: Any) -> str:
    # Accept RunReport with .trace (sequence of StepTrace with duration_ms), or a custom trace with .steps
    steps = None
    if hasattr(report_or_trace, "trace"):
        steps = report_or_trace.trace
    elif hasattr(report_or_trace, "steps"):
        steps = report_or_trace.steps
    else:
        return _fence("gantt\n  dateFormat X\n  axisFormat %L\n  %% (no steps)")
    durations = [getattr(s, "duration_ms", None) for s in steps]  # type: ignore[arg-type]
    if any(d is None for d in durations):
        return _fence("gantt\n  dateFormat X\n  axisFormat %L\n  %% (missing durations)")
    # Build cumulative start/end (ms)
    starts: list[int] = []
    ends: list[int] = []
    t = 0
    for d in durations:
        starts.append(int(t))
        t += float(d)
        ends.append(int(t))
    lines = ["gantt", "dateFormat X", "axisFormat %L", "section steps"]
    for i, s in enumerate(steps, 0):
        flag = "done" if getattr(s, "ok", True) else "crit"
        name = getattr(s, "name", f"step{i+1}")
        lines.append(f"{name}  :{flag}, step{i+1}, {starts[i]}, {ends[i]}")
    return _fence("\n".join(lines))


# ------------------------- Structured Plan visualization -------------------------


def _is_task(node: Any) -> bool:
    return hasattr(node, "name") and isinstance(node.name, str) and not hasattr(node, "items")


def _is_sequence(node: Any) -> bool:
    return hasattr(node, "items") and isinstance(node.items, (list, tuple)) and type(node).__name__ == "Sequence"


def _is_parallel(node: Any) -> bool:
    return hasattr(node, "items") and isinstance(node.items, (list, tuple)) and type(node).__name__ == "Parallel"


def _is_choose(node: Any) -> bool:
    return hasattr(node, "items") and isinstance(node.items, (list, tuple)) and type(node).__name__ == "Choose"


def _is_focus(node: Any) -> bool:
    return hasattr(node, "lens") and hasattr(node, "inner") and type(node).__name__ == "Focus"


def _is_loop(node: Any) -> bool:
    return hasattr(node, "predicate") and hasattr(node, "body") and type(node).__name__ == "LoopWhile"


def structured_plan_mermaid(plan: Any) -> str:
    """Render a structured plan (Task/Sequence/Parallel/Choose/Focus/LoopWhile)."""
    lines: list[str] = ["flowchart TD"]
    counter = {"n": 0}

    def nid() -> str:
        counter["n"] += 1
        return f"n{counter['n']}"

    def walk(node: Any) -> str:
        if _is_task(node):
            node_id = nid()
            lines.append(f'  {node_id}["task: {node.name}"]')
            return node_id
        if _is_sequence(node):
            seq_id = nid()
            lines.append(f'  {seq_id}((sequence))')
            prev = seq_id
            for child in node.items:
                cid = walk(child)
                lines.append(f"  {prev} --> {cid}")
                prev = cid
            return seq_id
        if _is_parallel(node):
            par_id = nid()
            lines.append(f'  {par_id}((parallel))')
            for child in node.items:
                cid = walk(child)
                lines.append(f"  {par_id} --> {cid}")
            return par_id
        if _is_choose(node):
            ch_id = nid()
            lines.append(f'  {ch_id}{{"choose"}}')
            for child in node.items:
                cid = walk(child)
                lines.append(f"  {ch_id} --> {cid}")
            return ch_id
        if _is_focus(node):
            f_id = nid()
            lines.append(f'  {f_id}[["focus(lens)"]]')
            cid = walk(node.inner)
            lines.append(f"  {f_id} --> {cid}")
            return f_id
        if _is_loop(node):
            l_id = nid()
            lines.append(f'  {l_id}{{"loop_while"}}')
            cid = walk(node.body)
            lines.append(f"  {l_id} --> {cid}")
            lines.append(f"  {cid} --> {l_id}")
            return l_id
        raise TypeError(f"Unknown structured plan node: {type(node).__name__}")

    root = walk(plan)
    lines.append(f"  start(((input))) --> {root}")
    lines.append(f"  {root} --> end(((output)))")
    return _fence("\n".join(lines))

# ---------------------------------- 2-cells ---------------------------------

@dataclass(frozen=True)
class TwoCellView:
    name: str
    src_name: str   # X
    tgt_name: str   # Y
    f_name: str     # f: X→Y
    g_name: str     # g: X→Y


def twocell_mermaid(alpha: TwoCellView) -> str:
    body = f"""
graph LR
  X["{alpha.src_name}"] -->|{alpha.f_name}| Y["{alpha.tgt_name}"]
  X -->|{alpha.g_name}| Y
  note["{alpha.name}: {alpha.f_name} ⇒ {alpha.g_name}"] -.-> Y
""".strip()
    return _fence(body)


def vcomp2_mermaid(alpha: TwoCellView, beta: TwoCellView) -> str:
    body = f"""
graph LR
  X["{alpha.src_name}"] -->|{alpha.f_name}| Y["{alpha.tgt_name}"]
  X -->|{alpha.g_name}| Y
  X -->|h| Y
  a["{alpha.name}: {alpha.f_name}⇒{alpha.g_name}"] -.-> Y
  b["{beta.name}: {alpha.g_name}⇒h"] -.-> Y
  comp["{beta.name} ∘₁ {alpha.name} : {alpha.f_name} ⇒ h"] -.-> Y
""".strip()
    return _fence(body)


def hcomp2_mermaid(left: TwoCellView, right: TwoCellView) -> str:
    body = f"""
flowchart LR
  subgraph L["Left 2-cell"]
    X["{left.src_name}"] -->|{left.f_name}| Y["{left.tgt_name}"]
    X -->|{left.g_name}| Y
    noteL["{left.name}: {left.f_name}⇒{left.g_name}"] -.-> Y
  end
  subgraph R["Right 2-cell"]
    Y2["Y"] -->|{right.f_name}| Z["{right.tgt_name}"]
    Y2 -->|{right.g_name}| Z
    noteR["{right.name}: {right.f_name}⇒{right.g_name}"] -.-> Z
  end
  comp["{right.name} ∘₂ {left.name} : {left.f_name}·{right.f_name} ⇒ {left.g_name}·{right.g_name}"] --> Z
""".strip()
    return _fence(body)


# --------------------------------- Orchestrator ------------------------------

def render_all(
    items: dict[str, Any], *, out_dir: str | None = None, naturality_sample_limit: int | None = 24
) -> dict[str, str]:
    """
    items: {name: object} where object can be:
      - Category-like (has .arrows or .morphisms)
      - Functor-like  (has .source, .target, .object_map)
      - Natural-like  (has .source, .target, .components)
      - Plan-like     (has .factors)
      - Report/trace  (has .trace (preferred) or .steps with name/ok/duration_ms)
      - TwoCellView   (this class)
    Returns: {filename.md: markdown_with_mermaid}
    If out_dir is provided, also writes files there.
    """
    out: dict[str, str] = {}

    def _write(fname: str, md: str) -> None:
        out[fname] = md
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            Path(out_dir, fname).write_text(md, encoding="utf-8")

    for name, obj in items.items():
        # Functor?
        if all(hasattr(obj, a) for a in ("source", "target", "object_map")):
            _write(f"{name}__functor.md", "# Functor\n\n" + functor_mermaid(obj))
            continue
        # Natural?
        if all(hasattr(obj, a) for a in ("source", "target", "components")):
            Fs = getattr(obj.source, "source", None)
            blocks: list[str] = ["# Natural Transformation"]
            if Fs is not None and hasattr(Fs, "arrows"):
                morphs = sorted(Fs.arrows, key=lambda a: _arr_name(a))
                cap = naturality_sample_limit or len(morphs)
                for i, a in enumerate(morphs):
                    if i >= cap:
                        break
                    blocks.append(f"\n## Naturality on `{_arr_name(a)}`\n\n" + naturality_mermaid(obj, a))
            _write(f"{name}__natural.md", "\n".join(blocks))
            continue
        # Diagram?
        if type(obj).__name__ == "Diagram" or (hasattr(obj, "edges") and not hasattr(obj, "arrows")):
            _write(f"{name}__diagram.md", "# Diagram\n\n" + diagram_mermaid(obj))
            continue
        # Category?
        if hasattr(obj, "arrows") or hasattr(obj, "morphisms"):
            _write(f"{name}__category.md", "# Category\n\n" + category_mermaid(obj))
            continue
        # Plan?
        if hasattr(obj, "factors"):
            _write(f"{name}__plan.md", "# Plan\n\n" + plan_mermaid(obj))
            continue
        # Trace/Report?
        if hasattr(obj, "trace") or hasattr(obj, "steps"):
            _write(f"{name}__trace.md", "# Execution Trace (Gantt)\n\n" + exec_gantt_mermaid(obj))
            continue
        # TwoCellView?
        if isinstance(obj, TwoCellView):
            _write(f"{name}__twocell.md", "# 2-Cell\n\n" + twocell_mermaid(obj))
            continue
        raise TypeError(f"Don't know how to render {name} ({type(obj).__name__})")

    return out


__all__ = [
    "category_mermaid",
    "diagram_mermaid",
    "functor_mermaid",
    "naturality_mermaid",
    "plan_mermaid",
    "structured_plan_mermaid",
    "exec_gantt_mermaid",
    "twocell_mermaid",
    "vcomp2_mermaid",
    "hcomp2_mermaid",
    "render_all",
    "TwoCellView",
]
