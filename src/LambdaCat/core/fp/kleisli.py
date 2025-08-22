from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Generic, List, Tuple, TypeVar, Type

from .typeclasses import FunctorT, ApplicativeT, MonadT
from ..builder import obj as _obj, arrow as _arrow, build_presentation
from ..category import Cat

A = TypeVar("A")
B = TypeVar("B") 
C = TypeVar("C")
M = TypeVar("M")


@dataclass(frozen=True)
class Kleisli(Generic[M, A, B]):
    """Kleisli arrow: A -> M[B] for monad M."""
    
    run: Callable[[A], M]
    
    def compose(self, other: "Kleisli[M, C, A]") -> "Kleisli[M, C, B]":
        """Compose Kleisli arrows: (self ∘ other)(c) = self(other(c)) >>= self.run"""
        return Kleisli(lambda c: other.run(c).bind(self.run))
    
    def then(self, other: Kleisli[M, B, C]) -> Kleisli[M, A, C]:
        """Sequential composition: self >>= other"""
        return other.compose(self)
    
    @classmethod
    def pure(cls, monad_cls: Type[M], value: B) -> "Kleisli[M, A, B]":
        """Pure arrow: pure(b) = λa. return b"""
        return cls(lambda _: monad_cls.pure(value))
    
    @classmethod  
    def id(cls, monad_cls: Type[M]) -> "Kleisli[M, A, A]":
        """Identity arrow: id = λa. return a"""
        return cls(lambda a: monad_cls.pure(a))
    
    def __call__(self, a: A) -> M:
        return self.run(a)


def kleisli_cat(monad_cls: Type[M], obj_type: type) -> type:
    """Create a Kleisli category for a given monad and object type."""
    
    class KleisliCategory:
        """Category where objects are types and morphisms are Kleisli arrows."""
        
        @staticmethod
        def identity(obj_type: type) -> Kleisli[M, object, object]:
            return Kleisli.pure(monad_cls, obj_type)
        
        @staticmethod
        def compose(g: Kleisli[M, object, object], f: Kleisli[M, object, object]) -> Kleisli[M, object, object]:
            return g.compose(f)
    
    return KleisliCategory


# Registry for monad instances  
_MONAD_REGISTRY: Dict[str, type] = {}


def register_monad(name: str, monad_cls: type) -> None:
    """Register a monad instance for use with Kleisli category builder.
    
    Args:
        name: Unique name for the monad
        monad_cls: The monad class implementing MonadT protocol
    """
    _MONAD_REGISTRY[name] = monad_cls


def get_registered_monads() -> Dict[str, type]:
    """Get all registered monad instances."""
    return dict(_MONAD_REGISTRY)


def kleisli_category_for(monad_name: str, objects: List[str]) -> "KleisliCat":
    """Build a concrete Kleisli category for a registered monad.
    
    Args:
        monad_name: Name of registered monad
        objects: List of object names for the category
        
    Returns:
        A concrete Kleisli category with the specified objects
        
    Raises:
        KeyError: If monad_name is not registered
    """
    if monad_name not in _MONAD_REGISTRY:
        available = list(_MONAD_REGISTRY.keys())
        raise KeyError(f"Monad '{monad_name}' not registered. Available: {available}")
    
    monad_cls = _MONAD_REGISTRY[monad_name]
    return KleisliCat(monad_name, objects, monad_cls)


class KleisliCat:
    """A concrete Kleisli category for a specific monad."""
    
    def __init__(self, name: str, objects: List[str], monad_cls: type):
        self.name = name
        self.objects = tuple(objects)
        self.monad_cls = monad_cls
        
        # Create identity arrows
        self.arrows: Dict[str, Kleisli[object, object, object]] = {}
        self.identities: Dict[str, str] = {}
        self.composition: Dict[Tuple[str, str], str] = {}
        
        for obj in objects:
            id_name = f"id:{obj}"
            id_arrow: Kleisli[object, object, object] = Kleisli.id(monad_cls)
            self.arrows[id_name] = id_arrow
            self.identities[obj] = id_name
            
            # Identity composition laws
            self.composition[(id_name, id_name)] = id_name
    
    def add_arrow(self, name: str, source: str, target: str, kleisli_fn: Kleisli[M, object, object]) -> "KleisliCat":
        """Add a Kleisli arrow to the category.
        
        Returns a new KleisliCat with the arrow added.
        """
        if source not in self.identities:
            raise ValueError(f"Source object {source} not in category")
        if target not in self.identities:
            raise ValueError(f"Target object {target} not in category")
        if name in self.arrows:
            raise ValueError(f"Arrow {name} already exists")
        
        # Create new category
        new_cat = KleisliCat(self.name, list(self.objects), self.monad_cls)
        new_cat.arrows = dict(self.arrows)
        new_cat.composition = dict(self.composition)
        
        new_cat.arrows[name] = kleisli_fn
        
        # Add identity composition laws for new arrow
        id_source = self.identities[source]
        id_target = self.identities[target]
        
        new_cat.composition[(name, id_source)] = name  # f ∘ id = f
        new_cat.composition[(id_target, name)] = name  # id ∘ f = f
        
        return new_cat
    
    def compose_arrows(self, left: str, right: str, result_name: str) -> "KleisliCat":
        """Add a composition of two arrows to the category.
        
        Args:
            left: Name of left arrow (applied second)
            right: Name of right arrow (applied first)  
            result_name: Name for the composite arrow
            
        Returns:
            New KleisliCat with the composition added
        """
        if left not in self.arrows:
            raise ValueError(f"Left arrow {left} not found")
        if right not in self.arrows:
            raise ValueError(f"Right arrow {right} not found")
        if result_name in self.arrows:
            raise ValueError(f"Result arrow {result_name} already exists")
        
        left_arrow = self.arrows[left]
        right_arrow = self.arrows[right]
        
        # Compose the Kleisli arrows
        composite = left_arrow.compose(right_arrow)
        
        # Create new category
        new_cat = KleisliCat(self.name, list(self.objects), self.monad_cls)
        new_cat.arrows = dict(self.arrows)
        new_cat.composition = dict(self.composition)
        
        new_cat.arrows[result_name] = composite
        new_cat.composition[(left, right)] = result_name
        
        return new_cat
    
    def __repr__(self) -> str:
        return f"KleisliCat({self.name}, |Obj|={len(self.objects)}, |Arr|={len(self.arrows)})"


# Auto-register common monads when module is imported
def _auto_register_monads() -> None:
    """Auto-register common monad instances."""
    try:
        from .instances.option import Option
        register_monad("Option", Option)
    except ImportError:
        pass
    
    try:
        from .instances.result import Result
        register_monad("Result", Result)
    except ImportError:
        pass
    
    try:
        from .instances.state import State
        register_monad("State", State)
    except ImportError:
        pass
    
    try:
        from .instances.reader import Reader
        register_monad("Reader", Reader)
    except ImportError:
        pass
    
    try:
        from .instances.writer import Writer
        register_monad("Writer", Writer)
    except ImportError:
        pass
    
    try:
        from .instances.list import List
        register_monad("List", List)
    except ImportError:
        pass


# Auto-register on import
_auto_register_monads()


# Utility functions for working with Kleisli arrows
def lift(f: Callable[[A], B], monad_cls: Type[M]) -> Kleisli[M, A, B]:
    """Lift a pure function to a Kleisli arrow."""
    return Kleisli(lambda a: monad_cls.pure(f(a)))


def join() -> Kleisli[object, object, object]:
    """Join operation as a Kleisli arrow."""
    return Kleisli(lambda mma: mma.bind(lambda ma: ma))


def fmap(f: Callable[[A], B]) -> Callable[[M], M]:
    """Functor map as a function."""
    return lambda ma: ma.map(f)


def ap(mf: M, ma: M) -> M:
    """Applicative ap as a function."""
    return mf.ap(ma)


def bind(ma: M, f: Callable[[A], M]) -> M:
    """Monad bind as a function."""
    return ma.bind(f)


# Structural category helper used by tests
def kleisli_category(
    name: str,
    objects: Tuple[str, ...] | List[str],
    morphisms: Dict[str, Tuple[str, str]],
    composition: Dict[Tuple[str, str], str],
) -> Cat:
    """Build a structural category from object and arrow specs.

    Notes:
    - Identity arrows with names starting with "id:" are ignored from `morphisms`
      and generated automatically; identity compositions are seeded automatically.
    - The provided `composition` mapping is merged over the seeded table.
    """
    # Build objects
    obj_list = [_obj(o) for o in objects]
    # Ignore identity-names in explicit morphisms; reserved for generated identities
    base_arrows = [_arrow(n, s, t) for n, (s, t) in morphisms.items() if not n.startswith("id:")]
    # Presentation and base category (with identities and their composition laws)
    pres = build_presentation(obj_list, base_arrows)
    base_cat = Cat.from_presentation(pres)
    # Merge composition tables, trusting caller to provide well-typed entries
    merged_comp: Dict[Tuple[str, str], str] = dict(base_cat.composition)
    merged_comp.update(composition)
    # Return concrete category
    return Cat(pres.objects, pres.arrows, merged_comp, base_cat.identities)

