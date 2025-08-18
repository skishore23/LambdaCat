from LambdaCat.core.presentation import Formal1
from LambdaCat.agents.runtime import sequential_functor


def test_agent_pipeline_runs():
	skills = {
		'denoise': lambda s: s.replace('~',''),
		'edges': lambda s: ''.join(ch for ch in s if ch.isalpha()),
		'segment': lambda s: s.upper(),
		'merge': lambda s: f"[{s}]",
	}
	plan = Formal1(('denoise','edges','segment','merge'))
	F = sequential_functor(skills)
	assert F(plan)("~a~b_c-1") == "[ABC]"

