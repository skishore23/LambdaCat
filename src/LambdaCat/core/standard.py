from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType

from .category import Cat
from .presentation import ArrowGen, Obj


def terminal_category(name: str = "Terminal") -> Cat:
    """
    >>> C = terminal_category()
    >>> C.compose('id:*', 'id:*')
    'id:*'
    """
    obj = Obj("*")
    id_name = "id:*"
    arrows = (ArrowGen(id_name, obj.name, obj.name),)
    composition = MappingProxyType({(id_name, id_name): id_name})
    identities = MappingProxyType({obj.name: id_name})
    return Cat(objects=(obj,), arrows=arrows, composition=dict(composition), identities=dict(identities))


def discrete(objects: list[str], name: str = "Discrete") -> Cat:
    """
    >>> C = discrete(["A","B"])
    >>> C.compose('id:A', 'id:A')
    'id:A'
    """
    objs = tuple(Obj(o) for o in objects)
    ids: dict[str, str] = {o.name: f"id:{o.name}" for o in objs}
    arrows = tuple(ArrowGen(ids[o.name], o.name, o.name) for o in objs)
    composition = MappingProxyType({(i, i): i for i in ids.values()})
    identities = MappingProxyType(ids)
    return Cat(objects=objs, arrows=arrows, composition=dict(composition), identities=dict(identities))


def simplex(n: int, name: str | None = None) -> Cat:
    """
    >>> Delta2 = simplex(2)
    >>> Delta2.compose('1->2', '0->1')
    '0->2'
    """
    # Δ^n with objects 0..n and unique i->j for i<=j
    objs = tuple(Obj(str(i)) for i in range(n + 1))
    ids: dict[str, str] = {o.name: f"id:{o.name}" for o in objs}
    arr: dict[tuple[int, int], str] = {}
    morph_names: set[str] = set()
    # identities
    for i, o in enumerate(objs):
        arr[(i, i)] = ids[o.name]
        morph_names.add(ids[o.name])
    # generating arrows i->j when i<j
    for i in range(n + 1):
        for j in range(i + 1, n + 1):
            name_ij = f"{i}->{j}"
            arr[(i, j)] = name_ij
            morph_names.add(name_ij)
    arrows = tuple(ArrowGen(arr[(i, j)], str(i), str(j)) for i in range(n + 1) for j in range(i, n + 1))
    # composition (g,f) where g: j->k, f: i->j yields i->k
    composition = MappingProxyType({
        (arr[(j, k)], arr[(i, j)]): arr[(i, k)]
        for i in range(n + 1) for j in range(i, n + 1) for k in range(j, n + 1)
    })
    identities = MappingProxyType(ids)
    return Cat(objects=objs, arrows=arrows, composition=dict(composition), identities=dict(identities))


def walking_isomorphism(name: str = "Iso") -> Cat:
    """
    >>> Iso = walking_isomorphism()
    >>> Iso.compose('g', 'f')
    'id:A'
    """
    A, B = Obj("A"), Obj("B")
    idA, idB = "id:A", "id:B"
    f, g = "f", "g"
    arrows = (
        ArrowGen(idA, A.name, A.name),
        ArrowGen(idB, B.name, B.name),
        ArrowGen(f, A.name, B.name),
        ArrowGen(g, B.name, A.name),
    )
    composition = MappingProxyType({
        (idA, idA): idA,
        (idB, idB): idB,
        (f, idA): f,
        (idB, f): f,
        (g, idB): g,
        (idA, g): g,
        (g, f): idA,
        (f, g): idB,
    })
    identities = MappingProxyType({A.name: idA, B.name: idB})
    return Cat(objects=(A, B), arrows=arrows, composition=dict(composition), identities=dict(identities))


def monoid_category(elements: Iterable[str], op: dict[tuple[str, str], str], unit: str) -> Cat:
    """
    Create a one-object category from a monoid.

    >>> elems = ['id:*', 'a', 'b']
    >>> op = {('id:*', 'id:*'): 'id:*', ('id:*', 'a'): 'a', ('a', 'id:*'): 'a',
    ...       ('a', 'a'): 'b', ('a', 'b'): 'a', ('b', 'a'): 'b', ('b', 'b'): 'a'}
    >>> C = monoid_category(elems, op, 'id:*')
    >>> C.compose('a', 'b')
    'a'
    """
    # One object category
    obj = Obj("*")
    objs = (obj,)

    # All elements become arrows from * to *
    arrows = tuple(ArrowGen(elem, "*", "*") for elem in elements)

    # Composition table from monoid operation
    composition = MappingProxyType(op)

    # Identity is the unit
    identities = MappingProxyType({"*": unit})

    return Cat(objects=objs, arrows=arrows, composition=dict(composition), identities=dict(identities))


def poset_category(P: Iterable[str], leq: dict[tuple[str, str], bool]) -> Cat:
    """
    >>> leq = {('A','A'): True, ('B','B'): True, ('A','B'): True}
    >>> C = poset_category(['A','B'], leq)
    >>> C.compose('A->B', 'id:A')
    'A->B'
    """
    """Poset as category: objects are elements; arrow x->y iff x ≤ y.

    leq provided as a boolean predicate table on pairs (x,y).
    """
    objs = tuple(Obj(x) for x in P)
    ids: dict[str, str] = {o.name: f"id:{o.name}" for o in objs}
    # Arrows: identities plus one arrow x->y whenever x ≤ y and x != y
    arrow_list: list[ArrowGen] = []
    for o in objs:
        arrow_list.append(ArrowGen(ids[o.name], o.name, o.name))
    for x in objs:
        for y in objs:
            if x.name != y.name and leq.get((x.name, y.name), False):
                arrow_list.append(ArrowGen(f"{x.name}->{y.name}", x.name, y.name))
    arrows = tuple(arrow_list)
    # composition: transitivity
    comp: dict[tuple[str, str], str] = {}
    for x in objs:
        for y in objs:
            for z in objs:
                if leq.get((x.name, y.name), False) and leq.get((y.name, z.name), False):
                    left = f"{y.name}->{z.name}" if y.name != z.name else f"id:{y.name}"
                    right = f"{x.name}->{y.name}" if x.name != y.name else f"id:{x.name}"
                    comp[(left, right)] = f"{x.name}->{z.name}" if x.name != z.name else f"id:{x.name}"
    composition = MappingProxyType(comp)
    identities = MappingProxyType(ids)
    return Cat(objects=objs, arrows=arrows, composition=dict(composition), identities=dict(identities))


def discrete_category(X: Iterable[str]) -> Cat:
    """Alias for discrete.
    >>> C = discrete_category(['X'])
    >>> C.compose('id:X','id:X')
    'id:X'
    """
    return discrete(list(X))


def delta_category(n: int) -> Cat:
    """Alias for simplex.
    >>> C = delta_category(1)
    >>> C.compose('1->1', '0->1') if ('1->1','0->1') in C.composition else 'id:0'
    'id:0'
    """
    return simplex(n)


