from dataclasses import dataclass
from typing import Any, Callable, Final, Generic, Tuple, TypeVar, Union
from ..core.presentation import Formal1


def action(name: str) -> str:
    return name


PLAN_MODE: Final[str] = "sequential"


State = TypeVar("State")
Ctx = TypeVar("Ctx")
Sub = TypeVar("Sub")


# Structured, composable plan algebra for agents (state-preserving)
@dataclass(frozen=True)
class Task(Generic[State, Ctx]):
    name: str


@dataclass(frozen=True)
class Sequence(Generic[State, Ctx]):
    items: Tuple["Plan[State, Ctx]", ...]


@dataclass(frozen=True)
class Parallel(Generic[State, Ctx]):
    items: Tuple["Plan[State, Ctx]", ...]


@dataclass(frozen=True)
class Choose(Generic[State, Ctx]):
    items: Tuple["Plan[State, Ctx]", ...]


@dataclass(frozen=True)
class Lens(Generic[State, Sub]):
    get: Callable[[State], Sub]
    set: Callable[[State, Sub], State]


@dataclass(frozen=True)
class Focus(Generic[State, Ctx, Sub]):
    lens: Lens[State, Sub]
    inner: "Plan[Sub, Ctx]"


@dataclass(frozen=True)
class LoopWhile(Generic[State, Ctx]):
    predicate: Callable[[State], bool]
    body: "Plan[State, Ctx]"


Plan = Union[
    Task[State, Ctx],
    Sequence[State, Ctx],
    Parallel[State, Ctx],
    Choose[State, Ctx],
    Focus[State, Ctx, Any],
    LoopWhile[State, Ctx],
]


def task(name: str) -> Plan[State, Ctx]:
    return Task(name)


def _as_plan(item: Union[Plan[State, Ctx], str]) -> Plan[State, Ctx]:
    return item if isinstance(item, (Task, Sequence, Parallel, Choose, Focus, LoopWhile)) else Task(str(item))



def choose(*items: Union[Plan[State, Ctx], str]) -> Plan[State, Ctx]:
    return Choose(tuple(_as_plan(i) for i in items))


# Preferred explicit name for parallel composition (alias of par)
def parallel(*items: Union[Plan[State, Ctx], str]) -> Plan[State, Ctx]:
    return Parallel(tuple(_as_plan(i) for i in items))


# Preferred explicit name for sequential composition (alias of seqp)
def sequence(*items: Union[Plan[State, Ctx], str]) -> Plan[State, Ctx]:
    return Sequence(tuple(_as_plan(i) for i in items))


def lens(get: Callable[[State], Sub], set: Callable[[State, Sub], State]) -> Lens[State, Sub]:
    return Lens(get=get, set=set)


def focus(l: Lens[State, Sub], inner: Plan[Sub, Ctx]) -> Plan[State, Ctx]:
    return Focus(lens=l, inner=inner)


def loop_while(predicate: Callable[[State], bool], body: Plan[State, Ctx]) -> Plan[State, Ctx]:
    return LoopWhile(predicate=predicate, body=body)

