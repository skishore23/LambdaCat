import pytest

from LambdaCat.core.functor import FunctorBuilder
from LambdaCat.core.laws import run_suite
from LambdaCat.core.laws_functor import FUNCTOR_SUITE
from LambdaCat.core.laws_natural import NATURAL_SUITE
from LambdaCat.core.natural import Natural
from LambdaCat.core.standard import simplex, walking_isomorphism


@pytest.mark.laws
@pytest.mark.functor_laws
@pytest.mark.natural_laws
def test_functor_and_naturality_suites_pass():
    Delta3 = simplex(3)
    Iso = walking_isomorphism()

    F = (
        FunctorBuilder("F", source=Delta3, target=Iso)
        .on_objects({"0": "A", "1": "A", "2": "B", "3": "B"})
        .on_morphisms({"0->1": "id:A", "1->2": "f", "2->3": "id:B", "0->3": "f"})
        .build()
    )

    assert run_suite(F, FUNCTOR_SUITE, config={"test_value": "test"}).ok

    eta = Natural(source=F, target=F, components={"0": "id:A", "1": "id:A", "2": "id:B", "3": "id:B"})
    assert run_suite(eta, NATURAL_SUITE).ok


