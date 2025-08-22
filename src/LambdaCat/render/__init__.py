"""LambdaCat rendering module with stable API."""

from .mermaid import (
    category_mermaid,
    diagram_mermaid, 
    functor_mermaid,
    naturality_mermaid,
    plan_mermaid,
    structured_plan_mermaid,
    exec_gantt_mermaid,
    twocell_mermaid,
    render_all,
)

try:
    from .graphviz import (
        category_dot,
        functor_dot,
        diagram_dot,
    )
    _HAS_GRAPHVIZ = True
except ImportError:
    _HAS_GRAPHVIZ = False
    
    def category_dot(*args, **kwargs):
        raise ImportError("Graphviz rendering requires 'graphviz' extra: pip install LambdaCat[viz]")
    
    def functor_dot(*args, **kwargs):
        raise ImportError("Graphviz rendering requires 'graphviz' extra: pip install LambdaCat[viz]")
    
    def diagram_dot(*args, **kwargs):
        raise ImportError("Graphviz rendering requires 'graphviz' extra: pip install LambdaCat[viz]")


__all__ = [
    # Mermaid renderers (always available)
    "category_mermaid",
    "diagram_mermaid",
    "functor_mermaid", 
    "naturality_mermaid",
    "plan_mermaid",
    "structured_plan_mermaid",
    "exec_gantt_mermaid",
    "twocell_mermaid",
    "render_all",
    # Graphviz renderers (optional)
    "category_dot",
    "functor_dot",
    "diagram_dot",
]
