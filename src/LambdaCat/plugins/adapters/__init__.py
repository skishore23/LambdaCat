from .. import require_plugin


def natural_adapter(*_args: object, **_kwargs: object) -> None:
	require_plugin("adapters.natural")

