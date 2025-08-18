from dataclasses import dataclass
from typing import Any, Callable, Final, Generic, Mapping, Tuple, TypeVar, Union
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


# ------------------------------ Actions registry ------------------------------


Fn = Callable[..., State]


@dataclass(frozen=True)
class Actions(Generic[State, Ctx]):
    _name_to_fn: Mapping[str, Fn]
    _fn_to_name: Mapping[Fn, str]

    @classmethod
    def empty(cls) -> "Actions[State, Ctx]":
        return cls(_name_to_fn={}, _fn_to_name={})

    def mapping(self) -> Mapping[str, Fn]:
        return dict(self._name_to_fn)

    def register(self, name: str, fn: Fn) -> "Actions[State, Ctx]":
        if not isinstance(name, str) or not name:
            raise AssertionError("Action name must be a non-empty string")
        if name in self._name_to_fn:
            raise AssertionError(f"Duplicate action name: {name}")
        if fn in self._fn_to_name and self._fn_to_name[fn] != name:
            raise AssertionError(f"Function already registered as '{self._fn_to_name[fn]}'")
        # Create fresh maps to preserve immutability
        new_n2f = dict(self._name_to_fn)
        new_f2n = dict(self._fn_to_name)
        new_n2f[name] = fn
        new_f2n[fn] = name
        return Actions(_name_to_fn=new_n2f, _fn_to_name=new_f2n)

    def name_of(self, fn: Fn) -> str:
        if fn not in self._fn_to_name:
            raise KeyError("Function not registered in Actions registry")
        return self._fn_to_name[fn]

    # ----------------------- Bound structured plan builders -----------------------

    def task(self, name_or_fn: Union[str, Fn]) -> Plan[State, Ctx]:
        if isinstance(name_or_fn, str):
            if name_or_fn not in self._name_to_fn:
                # Suggest close matches (fail-fast; no fallback)
                try:
                    from difflib import get_close_matches
                    matches = get_close_matches(name_or_fn, list(self._name_to_fn.keys()), n=3, cutoff=0.6)
                except Exception:
                    matches = []
                hint = f" Did you mean: {', '.join(matches)}" if matches else ""
                raise KeyError(f"Unknown action name: {name_or_fn}.{hint}")
            return task(name_or_fn)
        # Callable case
        name = self.name_of(name_or_fn)
        return task(name)

    def sequence(self, *items: Union[Plan[State, Ctx], str, Fn]) -> Plan[State, Ctx]:
        normalized: Tuple[Plan[State, Ctx], ...] = tuple(
            self._normalize_item(i) for i in items
        )
        return sequence(*normalized)

    def parallel(self, *items: Union[Plan[State, Ctx], str, Fn]) -> Plan[State, Ctx]:
        normalized: Tuple[Plan[State, Ctx], ...] = tuple(
            self._normalize_item(i) for i in items
        )
        return parallel(*normalized)

    def choose(self, *items: Union[Plan[State, Ctx], str, Fn]) -> Plan[State, Ctx]:
        normalized: Tuple[Plan[State, Ctx], ...] = tuple(
            self._normalize_item(i) for i in items
        )
        return choose(*normalized)

    def focus(self, l: Lens[State, Any], inner: Plan[Any, Ctx]) -> Plan[State, Ctx]:
        return focus(l, inner)

    def loop_while(self, predicate: Callable[[State], bool], body: Plan[State, Ctx]) -> Plan[State, Ctx]:
        return loop_while(predicate, body)

    # --------------------------------- Utilities ---------------------------------

    def _normalize_item(self, item: Union[Plan[State, Ctx], str, Fn]) -> Plan[State, Ctx]:
        if isinstance(item, (Task, Sequence, Parallel, Choose, Focus, LoopWhile)):
            return item
        if isinstance(item, str):
            return self.task(item)
        # Callable -> resolve to registered name
        return self.task(item)
