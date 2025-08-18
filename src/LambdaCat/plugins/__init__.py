"""Plugin registry (empty; disabled by default)."""

def require_plugin(name: str) -> None:
	raise RuntimeError(
		f"Plugin '{name}' not available. Install appropriate extras and enable explicitly."
	)

