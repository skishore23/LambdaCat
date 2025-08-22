from importlib.metadata import PackageNotFoundError, version

__all__ = [
	"core",
	"agents",
	"render",
	"functors",
	"monads",
	"diagrams",
	"extras",
	"plugins",
]

try:
	__version__ = version("LambdaCat")
except PackageNotFoundError:
	__version__ = "0.0.0"

# Minimal friendly re-exports for the new core API
from .core.presentation import ArrowGen, Formal1, Obj, Presentation  # noqa: E402,F401
