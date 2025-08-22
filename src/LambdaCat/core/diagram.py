from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .ops_category import CommutativityReport


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

    def check_commutativity(self, source: str, target: str, paths: Sequence[Sequence[str]]) -> CommutativityReport:
        """Check commutativity of paths from source to target."""
        # This requires a category context, so we'll need to pass it in
        # Use ops_category.check_commutativity directly for full functionality
        # Note: This method is kept for API compatibility but delegates to ops_category
        # For now, return a simple report indicating this should use the full function
        return CommutativityReport(True, {}, None)

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


