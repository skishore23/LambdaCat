from __future__ import annotations

from collections.abc import Sequence
from types import MappingProxyType

from .category import Cat
from .presentation import Obj


def opposite_category(C: Cat) -> Cat:
    # create op arrow names by suffixing ^op and swapping endpoints
    tuple(
        (f"{a.name}^op", a.target, a.source) for a in C.arrows
    )
    # mapping original name -> op name
    to_op: dict[str, str] = {a.name: f"{a.name}^op" for a in C.arrows}
    # composition: (g^op, f^op) = (f∘g)^op in C^op
    comp = MappingProxyType({
        (to_op[g], to_op[f]): to_op[gf] for (g, f), gf in C.composition.items()
    })
    ids = MappingProxyType({o.name: to_op[C.identities[o.name]] for o in C.objects})
    # rebuild ArrowGen list with swapped endpoints
    arrows = tuple(
        type(C.arrows[0])(to_op[a.name], a.target, a.source) for a in C.arrows
    )
    return Cat(objects=C.objects, arrows=arrows, composition=dict(comp), identities=dict(ids))



# --------------------------- Diagrams and paths ---------------------------

def paths(C: Cat, source: str, target: str, *, max_length: int = 4) -> list[list[str]]:
    """Enumerate arrow-name paths from source to target up to max_length.

    Paths are sequences [f1, f2, ..., fn] such that dom(f1)=source, cod(fi)=dom(f{i+1}), cod(fn)=target.
    """
    if max_length < 0:
        raise ValueError("max_length must be non-negative")
    by_name = {a.name: a for a in C.arrows}
    # adjacency: from object name -> list of outgoing arrow names
    out: dict[str, list[str]] = {}
    for a in C.arrows:
        out.setdefault(a.source, []).append(a.name)

    results: list[list[str]] = []

    def extend(current_obj: str, acc: list[str], depth: int) -> None:
        if depth > max_length:
            return
        if current_obj == target and acc:
            results.append(list(acc))
        for f in out.get(current_obj, []):
            nxt = by_name[f].target
            acc.append(f)
            extend(nxt, acc, depth + 1)
            acc.pop()

    extend(source, [], 0)
    return results


class CommutativityReport:
    def __init__(self, ok: bool, composites: dict[tuple[str, ...], str], mismatch: tuple[tuple[str, ...], tuple[str, ...]] | None):
        self.ok = ok
        self.composites = composites
        self.mismatch = mismatch

    def to_text(self) -> str:
        if self.ok:
            return "[✓] commutative"
        assert self.mismatch is not None
        (p1, p2) = self.mismatch
        return f"[✗] paths do not agree: {p1} vs {p2}"


def check_commutativity(C: Cat, A: str, B: str, candidate_paths: Sequence[Sequence[str]]) -> CommutativityReport:
    """Check that all provided paths from A to B have equal composites in C.

    Returns CommutativityReport with computed composites and first mismatch.
    """
    composites: dict[tuple[str, ...], str] = {}
    for p in candidate_paths:
        if not p:
            continue
        # typed fold using C.compose
        try:
            acc = p[0]
            # Verify dom(acc)==A
            a0 = next(a for a in C.arrows if a.name == acc)
            if a0.source != A:
                raise TypeError(f"path starts at {a0.source}, expected {A}")
            # Compose remaining arrows: for path [f, g, h], compute h∘(g∘f)
            for f in p[1:]:
                # Note: C.compose(left, right) means left∘right
                # So for path [f, g], we want g∘f, so compose(g, f)
                acc = C.compose(f, acc)
            # Verify cod==B
            ah = next(a for a in C.arrows if a.name == acc)
            if ah.target != B:
                # Skip paths that don't end at the target - they're not valid for commutativity
                continue
        except Exception:
            # Skip paths that have composition errors
            continue
        composites[tuple(p)] = acc

    # If no valid paths, return success (trivially commutative)
    if not composites:
        return CommutativityReport(True, composites, None)

    # Pairwise compare
    items = list(composites.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][1] != items[j][1]:
                return CommutativityReport(False, composites, (items[i][0], items[j][0]))
    return CommutativityReport(True, composites, None)


# ------------------------------ Slice category ------------------------------

def slice_category(C: Cat, A: str) -> Cat:
    """Construct the slice category C/A.

    - Objects: arrows f: A -> X in C (represented by their arrow names)
    - Morphisms: for f: A->X and g: A->Y, a morphism f -> g is an arrow h: X->Y in C such that h ∘ f = g
      We name such morphisms as "h[f->g]" to ensure global uniqueness.
    """
    from .presentation import ArrowGen
    # Collect objects: all arrows with source A
    objs = tuple(Obj(a.name) for a in C.arrows if a.source == A)
    {o.name for o in objs}  # equal to f-names
    # identities in slice: for each f: A->X, identity is id_X with witness id_X ∘ f = f
    ids: dict[str, str] = {}
    arrows_list: list[tuple[str, str, str]] = []  # (name, src_obj, tgt_obj) in slice
    # Map arrow names to underlying ArrowGen for typing
    by_name = {a.name: a for a in C.arrows}
    # Build all candidate morphisms: for f and g, any h: X->Y with h∘f = g
    for f in objs:
        f_arr = by_name[f.name]
        # identity of object f is id_{cod(f)} witnessed by composition
        id_X = C.identities[f_arr.target]
        try:
            if C.compose(id_X, f.name) == f.name:
                ids[f.name] = f"id:{f.name}"
                arrows_list.append((ids[f.name], f.name, f.name))
        except Exception:
            pass
    # Now non-identity morphisms
    for f in objs:
        X = by_name[f.name].target
        for g in objs:
            Y = by_name[g.name].target
            # Scan all h: X->Y
            for h in C.arrows:
                if h.source == X and h.target == Y:
                    try:
                        if C.compose(h.name, f.name) == g.name:
                            name = f"h[{h.name}]:{f.name}->{g.name}"
                            arrows_list.append((name, f.name, g.name))
                    except Exception:
                        continue
    # Build Cat pieces
    tuple(ArrowGen(name, src, tgt) for (name, src, tgt) in arrows_list)
    # composition: inherited from C on underlying h names
    comp: dict[tuple[str, str], str] = {}
    # Identities already added: (id_f, id_f) -> id_f
    for f in objs:
        idf = f"id:{f.name}"
        if idf in {n for (n, _, _) in arrows_list}:
            comp[(idf, idf)] = idf
    # Compose two morphisms h1[f->g] and h2[g->k] yields (h2∘h1)[f->k]
    # We can parse names back
    def _parse(name: str) -> tuple[str, str, str] | None:
        # format: h[H]:F->G
        if not name.startswith("h[") or "]:" not in name or "->" not in name:
            return None
        H = name[2:name.index("]:")]
        rest = name[name.index("]:") + 2 :]
        F, G = rest.split("->", 1)
        return (H, F, G)
    names = {n for (n, _, _) in arrows_list}
    for n2, _s2, _t2 in arrows_list:
        for n1, _s1, _t1 in arrows_list:
            p2 = _parse(n2)
            p1 = _parse(n1)
            if p2 is None or p1 is None:
                continue
            # types: n2: g->k, n1: f->g
            H2, G, K = p2
            H1, F, G2 = p1
            if G2 != G:
                continue
            try:
                H = C.compose(H2, H1)
            except Exception:
                continue
            n = f"h[{H}]:{F}->{K}"
            if n in names:
                comp[(n2, n1)] = n
    identities = MappingProxyType(ids)
    composition = MappingProxyType(comp)
    # ArrowGen constructor type reuse
    if C.arrows:
        ArrowGen = type(C.arrows[0])
        arrows = tuple(ArrowGen(n, s, t) for (n, s, t) in arrows_list)
    else:
        arrows = ()
    return Cat(objects=objs, arrows=arrows, composition=dict(composition), identities=dict(identities))

