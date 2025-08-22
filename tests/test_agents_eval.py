from LambdaCat.agents.eval import choose_best, quick_functor_laws, run_plan
from LambdaCat.core.presentation import Formal1


def test_run_and_choose_best():
	impl = {
		'denoise': lambda s, ctx=None: s.replace('~',''),
		'edges': lambda s, ctx=None: ''.join(ch for ch in s if ch.isalpha()),
		'segment': lambda s, ctx=None: s.upper(),
		'merge': lambda s, ctx=None: f"[{s}]",
	}
	plan1 = Formal1(('denoise','edges','segment','merge'))
	plan2 = Formal1(('denoise','segment','merge'))

	report1 = run_plan(plan1, impl, "~a~b_c-1", evaluator=lambda o: -len(o))
	assert report1.output == "[ABC]" and report1.score == -5

	best_plan, best_report = choose_best([plan1, plan2], impl, "~a~b_c-1", evaluator=lambda o: -len(o))
	assert best_plan.factors == plan1.factors and best_report.output == "[ABC]"


def test_quick_functor_laws():
	impl = {
		'f': lambda x, ctx=None: x + 1,
		'g': lambda x, ctx=None: x * 2,
		'id': lambda x, ctx=None: x,
	}
	quick_functor_laws(impl, id_name='id', samples=[0,1,2])

