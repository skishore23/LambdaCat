from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .ops_category import CommutativityReport

if TYPE_CHECKING:
    from .category import Cat


@dataclass(frozen=True)
class Diagram:
    """Minimal directed multigraph over named objects with labeled edges.

    objects: sequence of object names.
    edges: list of (src, tgt, arrow_name) triplets.
    """
    objects: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]

    @staticmethod
    def from_edges(objects: Iterable[str], edges: Iterable[tuple[str, str, str]]) -> Diagram:
        objs = tuple(objects)
        objset = set(objs)
        es = tuple(edges)
        for (s, t, _) in es:
            if s not in objset or t not in objset:
                raise ValueError(f"edge endpoints must be in objects: {s}->{t}")
        return Diagram(objs, es)

    def check_commutativity(self, C: Cat, source: str, target: str, paths: Sequence[Sequence[str]]) -> CommutativityReport:
        """Check that provided paths from source to target commute in category C."""
        from .ops_category import check_commutativity
        return check_commutativity(C, source, target, paths)

    def to_mermaid(self) -> str:
        """Render diagram as Mermaid graph."""
        lines = ["graph TD"]
        for src, tgt, label in self.edges:
            lines.append(f"    {src} -->|{label}| {tgt}")
        return "\n".join(lines)

    def to_dot(self) -> str:
        """Render diagram as Graphviz DOT format."""
        lines = ["digraph G {"]
        lines.append("    rankdir=LR;")
        for src, tgt, label in self.edges:
            lines.append(f'    "{src}" -> "{tgt}" [label="{label}"];')
        lines.append("}")
        return "\n".join(lines)

    def paths(self, source: str, target: str, max_length: int = 4) -> list[list[str]]:
        """Find all paths from source to target up to max_length."""
        # This is a simplified path finding that doesn't require category context
        # For full path finding with composition, use ops_category.paths
        if source not in self.objects or target not in self.objects:
            return []

        # Build adjacency list
        adj: dict[str, list[tuple[str, str]]] = {}
        for src, tgt, label in self.edges:
            if src not in adj:
                adj[src] = []
            adj[src].append((tgt, label))

        results: list[list[str]] = []

        def dfs(current: str, path: list[str], depth: int) -> None:
            if depth > max_length:
                return
            if current == target and path:
                results.append(path[:])
            if current in adj:
                for next_obj, edge_label in adj[current]:
                    path.append(edge_label)
                    dfs(next_obj, path, depth + 1)
                    path.pop()

        dfs(source, [], 0)
        return results


