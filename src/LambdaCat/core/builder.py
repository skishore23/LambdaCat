from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from .presentation import Obj, ArrowGen, Formal1, Presentation


def obj(name: str, data: object | None = None) -> Obj:
	return Obj(name, data)


def arrow(name: str, source: str, target: str) -> ArrowGen:
	return ArrowGen(name, source, target)


def _identity_name(object_name: str) -> str:
	return f"id:{object_name}"


def _identities_for(objects: Iterable[Obj]) -> Tuple[ArrowGen, ...]:
	return tuple(ArrowGen(_identity_name(o.name), o.name, o.name) for o in objects)


def build_presentation(
	objects: Iterable[Obj],
	arrows: Iterable[ArrowGen],
	relations: Iterable[tuple[Formal1, Formal1]] = (),
) -> Presentation:
	objs: Tuple[Obj, ...] = tuple(objects)
	# Validate unique object names
	obj_names = [o.name for o in objs]
	if len(set(obj_names)) != len(obj_names):
		raise ValueError("Duplicate object name detected")
	# Validate arrow endpoints and reserved identity namespace on provided arrows
	base_arrows: Tuple[ArrowGen, ...] = tuple(arrows)
	for a in base_arrows:
		if a.source not in obj_names or a.target not in obj_names:
			raise ValueError(f"Arrow endpoint not found among objects: {a}")
		if a.name.startswith("id:"):
			raise ValueError(f"Arrow name conflicts with reserved identity namespace: {a.name}")
	gens: Tuple[ArrowGen, ...] = base_arrows + _identities_for(objs)
	_names = set()
	for g in gens:
		if g.name in _names:
			raise ValueError(f"Duplicate arrow name: {g.name}")
		_names.add(g.name)
	return Presentation(objs, gens, tuple(relations))

