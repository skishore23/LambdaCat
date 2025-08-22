from .adjunctions import ADJUNCTION_SUITE, Adjunction, free_forgetful_adjunction
from .builder import arrow, build_presentation, obj
from .category import Cat
from .diagram import Diagram
from .fp.typeclasses import ApplicativeT, FunctorT, MonadT, Monoid, Semigroup
from .functor import Functor, FunctorBuilder, apply_functor
from .laws import Law, LawResult, LawSuite, SuiteReport, Violation, run_suite
from .laws_applicative import APPLICATIVE_SUITE
from .laws_category import CATEGORY_SUITE
from .laws_functor import FUNCTOR_SUITE
from .laws_monad import MONAD_SUITE
from .laws_natural import NATURAL_SUITE
from .limits import Cone, Limit, equalizer, initial_object, product, terminal_object
from .natural import Natural, check_naturality
from .optics import Iso, Lens, Prism, focus, iso, lens, preview, prism, review, set_value, view
from .presentation import ArrowGen, Formal1, Obj, Presentation

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

