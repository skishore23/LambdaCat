from __future__ import annotations

from typing import Dict, Any

from .presentation import Obj, ArrowGen, Formal1, Presentation


def to_dict(p: Presentation) -> Dict[str, Any]:
	return {
		"objects": [{"name": o.name, "data": o.data} for o in p.objects],
		"arrows": [
			{"name": a.name, "source": a.source, "target": a.target} for a in p.arrows
		],
		"relations": [
			{"lhs": list(lhs.factors), "rhs": list(rhs.factors)} for lhs, rhs in p.relations
		],
	}


def from_dict(d: Dict[str, Any]) -> Presentation:
	objects = tuple(Obj(x["name"], x.get("data")) for x in d["objects"])
	# Validate unique object names
	obj_names = [o.name for o in objects]
	if len(set(obj_names)) != len(obj_names):
		raise ValueError("Duplicate object name detected in input")
	arrows = tuple(ArrowGen(x["name"], x["source"], x["target"]) for x in d["arrows"])
	# Validate arrow names unique and endpoints exist
	seen = set()
	for a in arrows:
		if a.name in seen:
			raise ValueError(f"Duplicate arrow name detected in input: {a.name}")
		seen.add(a.name)
		if a.source not in obj_names or a.target not in obj_names:
			raise ValueError(f"Arrow endpoint not found among objects in input: {a}")
	relations = tuple(
		(Formal1(tuple(rel["lhs"])), Formal1(tuple(rel["rhs"])) )
		for rel in d.get("relations", [])
	)
	# Validate relation factors refer to known arrows
	arrow_names = {a.name for a in arrows}
	for lhs, rhs in relations:
		for f in (*lhs.factors, *rhs.factors):
			if f not in arrow_names:
				raise ValueError(f"Relation references unknown arrow: {f}")
	return Presentation(objects, arrows, relations)

