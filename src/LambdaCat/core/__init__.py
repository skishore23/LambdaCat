from .presentation import Obj, ArrowGen, Formal1, Presentation
from .category import Cat
from .builder import obj, arrow, build_presentation
from .functor import Functor, apply_functor, FunctorBuilder
from .natural import Natural, check_naturality
from .laws import Law, LawSuite, Violation, LawResult, SuiteReport, run_suite
from .laws_category import CATEGORY_SUITE
from .laws_natural import NATURAL_SUITE
from .laws_functor import FUNCTOR_SUITE
from .laws_applicative import APPLICATIVE_SUITE
from .laws_monad import MONAD_SUITE
from .diagram import Diagram
from .optics import Lens, Prism, Iso, lens, prism, iso, view, set_value, focus, preview, review
from .limits import Cone, Limit, product, equalizer, terminal_object, initial_object
from .adjunctions import Adjunction, ADJUNCTION_SUITE, free_forgetful_adjunction
from .fp.typeclasses import FunctorT, ApplicativeT, MonadT, Semigroup, Monoid

__all__ = [
	# Core types
	"Obj",
	"ArrowGen", 
	"Formal1",
	"Presentation",
	"Cat",
	# Builders
	"obj",
	"arrow",
	"build_presentation",
	# Functors & Natural transformations
	"Functor",
	"FunctorBuilder",
	"apply_functor",
	"Natural",
	"check_naturality",
	# Laws
	"Law",
	"LawSuite",
	"Violation",
	"LawResult", 
	"SuiteReport",
	"run_suite",
	"CATEGORY_SUITE",
	"FUNCTOR_SUITE",
	"APPLICATIVE_SUITE",
	"MONAD_SUITE",
	"NATURAL_SUITE",
	# Diagrams
	"Diagram",
	# Optics
	"Lens",
	"Prism", 
	"Iso",
	"lens",
	"prism",
	"iso",
	"view",
	"set_value",
	"focus",
	"preview",
	"review",
	# Typeclasses
		"FunctorT",
	"ApplicativeT", 
	"MonadT",
	"Semigroup",
	"Monoid",
	# Limits and colimits
	"Cone",
	"Limit",
	"product",
	"equalizer",
	"terminal_object",
	"initial_object",
	# Adjunctions
	"Adjunction",
	"ADJUNCTION_SUITE",
	"free_forgetful_adjunction",
]

