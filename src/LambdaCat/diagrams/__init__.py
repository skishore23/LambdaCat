from __future__ import annotations

from LambdaCat.core.diagram import Diagram
from LambdaCat.render.mermaid import diagram_mermaid
try:
    from LambdaCat.render.graphviz import diagram_dot
    _HAS_GRAPHVIZ = True
except ImportError:
    _HAS_GRAPHVIZ = False
    def diagram_dot(*args, **kwargs):
        raise ImportError("Graphviz rendering requires 'graphviz' extra: pip install LambdaCat[viz]")

__all__ = ["Diagram", "diagram_mermaid", "diagram_dot"]


