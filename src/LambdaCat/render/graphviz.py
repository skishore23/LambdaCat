"""Graphviz DOT rendering for LambdaCat structures."""

from __future__ import annotations

from typing import Any, Iterable, List, Protocol

try:
    import graphviz
    _HAS_GRAPHVIZ = True
except ImportError:
    _HAS_GRAPHVIZ = False
    graphviz = None


class _ArrowLike(Protocol):
    source: Any
    target: Any
    name: Any


class _CategoryLike(Protocol):
    arrows: Iterable[_ArrowLike]


def _iter_arrows(category: Any) -> Iterable[_ArrowLike]:
    """Support our core Cat (.arrows of ArrowGen) and any foreign shape with .morphisms."""
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


def category_dot(C: _CategoryLike | Any, *, hide_id: bool = True, format: str = "svg") -> str:
    """Render a category as Graphviz DOT format."""
    if not _HAS_GRAPHVIZ:
        raise ImportError("Graphviz rendering requires 'graphviz' package: pip install graphviz")
    
    dot = graphviz.Digraph(comment="Category", format=format)
    dot.attr(rankdir="LR")
    
    # Add nodes (objects)
    objects = set()
    for arrow in _iter_arrows(C):
        objects.add(_src_name(arrow))
        objects.add(_tgt_name(arrow))
    
    for obj in sorted(objects):
        dot.node(obj, obj)
    
    # Add edges (morphisms)
    arrows = sorted(_iter_arrows(C), key=lambda a: _arr_name(a))
    for arrow in arrows:
        name = _arr_name(arrow)
        if hide_id and _src_name(arrow) == _tgt_name(arrow) and (name.startswith("id:") or name.startswith("id_")):
            continue
        dot.edge(_src_name(arrow), _tgt_name(arrow), label=name)
    
    return dot.source


def functor_dot(F: Any, *, format: str = "svg") -> str:
    """Render a functor as Graphviz DOT format."""
    if not _HAS_GRAPHVIZ:
        raise ImportError("Graphviz rendering requires 'graphviz' package: pip install graphviz")
    
    dot = graphviz.Digraph(comment="Functor", format=format)
    dot.attr(rankdir="TB")
    
    # Source category subgraph
    with dot.subgraph(name="cluster_source") as s:
        s.attr(label="Source Category")
        s.attr(style="filled", color="lightgrey")
        
        # Source objects and arrows
        for arrow in sorted(_iter_arrows(F.source), key=lambda a: _arr_name(a)):
            src, tgt = _src_name(arrow), _tgt_name(arrow)
            s.node(f"S_{src}", src)
            s.node(f"S_{tgt}", tgt)
            s.edge(f"S_{src}", f"S_{tgt}", label=_arr_name(arrow))
    
    # Target category subgraph  
    with dot.subgraph(name="cluster_target") as t:
        t.attr(label="Target Category")
        t.attr(style="filled", color="lightblue")
        
        # Target objects and arrows
        for arrow in sorted(_iter_arrows(F.target), key=lambda a: _arr_name(a)):
            src, tgt = _src_name(arrow), _tgt_name(arrow)
            t.node(f"T_{src}", src)
            t.node(f"T_{tgt}", tgt)
            t.edge(f"T_{src}", f"T_{tgt}", label=_arr_name(arrow))
    
    # Functor mappings (dashed edges)
    if hasattr(F, "object_map") and isinstance(F.object_map, dict):
        for s_name, t_name in sorted(F.object_map.items()):
            dot.edge(f"S_{s_name}", f"T_{t_name}", style="dashed", color="red")
    
    return dot.source


def diagram_dot(D: Any, *, format: str = "svg") -> str:
    """Render a diagram as Graphviz DOT format."""
    if not _HAS_GRAPHVIZ:
        raise ImportError("Graphviz rendering requires 'graphviz' package: pip install graphviz")
    
    dot = graphviz.Digraph(comment="Diagram", format=format)
    dot.attr(rankdir="LR")
    
    # Add edges from diagram
    for (s, t, name) in getattr(D, "edges", ()):  # type: ignore[attr-defined]
        dot.edge(str(s), str(t), label=str(name))
    
    return dot.source
