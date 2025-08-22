from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Obj:
	name: str
	data: Optional[object] = None


@dataclass(frozen=True)
class ArrowGen:
	name: str
	source: str
	target: str


@dataclass(frozen=True)
class Formal1:
	# h∘...∘g∘f (rightmost applied first)
	factors: tuple[str, ...]


@dataclass(frozen=True)
class Presentation:
	objects: tuple[Obj, ...]
	arrows: tuple[ArrowGen, ...]
	relations: tuple[tuple[Formal1, Formal1], ...] = ()

