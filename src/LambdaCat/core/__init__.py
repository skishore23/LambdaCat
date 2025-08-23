from .adjunctions import ADJUNCTION_SUITE, Adjunction, free_forgetful_adjunction
from .builder import arrow, build_presentation, normalize, obj
from .category import Cat
from .diagram import Diagram
from .fp.typeclasses import ApplicativeT, FunctorT, MonadT, Monoid, Semigroup
from .functor import Functor, FunctorBuilder, apply_functor
from .graphviz_helpers import (
    check_graphviz_available,
    render_dot_string,
    render_to_file,
    safe_render_example,
)
from .hom_helpers import hom, is_iso, iso_classes, iso_inverse
from .laws import Law, LawResult, LawSuite, SuiteReport, Violation, run_suite
from .laws_applicative import APPLICATIVE_SUITE
from .laws_category import CATEGORY_SUITE
from .laws_functor import FUNCTOR_SUITE
from .laws_monad import MONAD_SUITE
from .laws_natural import NATURAL_SUITE
from .limits import Cone, Limit, equalizer, initial_object, product, terminal_object
from .limits_diagnostics import (
    EqualizerFailure,
    ProductFailure,
    diagnose_equalizer_failure,
    diagnose_product_failure,
    suggest_product_construction,
)
from .natural import Natural, check_naturality
from .optics import Iso, Lens, Prism, focus, iso, lens, preview, prism, review, set_value, view
from .presentation import ArrowGen, Formal1, Obj, Presentation
from .standard import (
    delta_category,
    discrete,
    discrete_category,
    monoid_category,
    poset_category,
    simplex,
    terminal_category,
    walking_isomorphism,
)

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
	"normalize",
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
	# Graphviz helpers
	"render_to_file",
	"render_dot_string",
	"check_graphviz_available",
	"safe_render_example",
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
	# Limits diagnostics
	"ProductFailure",
	"EqualizerFailure",
	"diagnose_product_failure",
	"diagnose_equalizer_failure",
	"suggest_product_construction",
	# Adjunctions
	"Adjunction",
	"ADJUNCTION_SUITE",
	"free_forgetful_adjunction",
	# Standard categories
	"discrete",
	"discrete_category",
	"simplex",
	"delta_category",
	"walking_isomorphism",
	"terminal_category",
	"monoid_category",
	"poset_category",
	# Hom-set helpers
	"hom",
	"is_iso",
	"iso_inverse",
	"iso_classes",
]

