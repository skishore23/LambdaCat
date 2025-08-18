from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Mapping

from LambdaCat.core.presentation import Formal1
from LambdaCat.agents import (
    Agent,
    AgentBuilder,
    Actions,
    task,
    sequence,
    parallel,
    choose,
    lens,
    focus,
    run_structured_plan,
    quick_functor_laws,
    concat,
    first,
    argmax,
)
from LambdaCat.agents.actions import loop_while
from LambdaCat.extras.viz_mermaid import plan_mermaid, structured_plan_mermaid, exec_gantt_mermaid
from pathlib import Path


# -----------------------------
# Pure actions (state -> state)
# -----------------------------

def identity(x: str, ctx: Any | None = None) -> str:
    return x


def strip_ws(x: str, ctx: Any | None = None) -> str:
    return x.strip()


def to_lower(x: str, ctx: Any | None = None) -> str:
    return x.lower()


def remove_noise(x: str, ctx: Any | None = None) -> str:
    allowed = []
    for ch in x:
        if ch.isalnum() or ch.isspace():
            allowed.append(ch)
    return "".join(allowed)


def normalize_ws(x: str, ctx: Any | None = None) -> str:
    return " ".join(x.split())


def summarize_head(x: str, ctx: Any | None = None) -> str:
    # very small, deterministic "summary": first sentence or first 80 chars
    head = x.split(".")[0]
    return head if head else (x[:80])


def extract_keywords(x: str, ctx: Any | None = None) -> str:
    # toy keyword extraction: unique words longer than 3, sorted
    words = [w for w in x.split() if len(w) > 3]
    uniq = sorted(set(words))
    return " ".join(uniq)


def to_upper(x: str, ctx: Any | None = None) -> str:
    return x.upper()


Implementation: Mapping[str, Callable[..., str]] = {
    "identity": identity,
    "strip_ws": strip_ws,
    "to_lower": to_lower,
    "remove_noise": remove_noise,
    "normalize_ws": normalize_ws,
    "summarize_head": summarize_head,
    "extract_keywords": extract_keywords,
    "to_upper": to_upper,
}

# Also expose a registry-based interface
Registry = (
    Actions[str, Any].empty()
    .register("identity", identity)
    .register("strip_ws", strip_ws)
    .register("to_lower", to_lower)
    .register("remove_noise", remove_noise)
    .register("normalize_ws", normalize_ws)
    .register("summarize_head", summarize_head)
    .register("extract_keywords", extract_keywords)
    .register("to_upper", to_upper)
)


# -----------------------------
# Demo 1: Linear plan + chooser
# -----------------------------

def demo_linear_plan(input_text: str) -> None:
    plan_a = Formal1(("strip_ws", "remove_noise", "normalize_ws"))
    plan_b = Formal1(("strip_ws", "to_lower", "normalize_ws"))

    agent = Agent(implementation=Implementation, evaluator=lambda out: -len(out))
    best_plan, report = agent.choose_best([plan_a, plan_b], input_text)

    print("[Linear] chosen:", best_plan.factors)
    print("[Linear] output:", report.output)


# ---------------------------------------------
# Demo 2: Structured plan (parallel + choose)
# ---------------------------------------------

def demo_structured_plan(input_text: str) -> None:
    # Using free builders
    plan = sequence(
        task("strip_ws"),
        task("remove_noise"),
        parallel(task("summarize_head"), task("extract_keywords")),
        choose(task("to_upper"), task("identity")),
    )

    # Using registry-bound builders (same plan)
    _ = Registry.sequence(
        Registry.task(strip_ws),
        Registry.task(remove_noise),
        Registry.parallel(Registry.task(summarize_head), Registry.task(extract_keywords)),
        Registry.choose(Registry.task(to_upper), Registry.task("identity")),
    )

    report = run_structured_plan(
        plan,
        Implementation,
        input_value=input_text,
        aggregate_fn=concat(" | "),
        choose_fn=first(),
        snapshot=True,
    )
    print("[Structured] output:", report.output)

    # Visuals to console (Mermaid)
    linear = Formal1(("strip_ws", "remove_noise", "normalize_ws"))
    print(plan_mermaid(linear))
    print(structured_plan_mermaid(plan))
    print(exec_gantt_mermaid(report))


# ---------------------------------
# Demo 3: Lens focus on nested state
# ---------------------------------

@dataclass(frozen=True)
class Article:
    title: str
    body: str


def _article_body_get(a: Article) -> str:
    return a.body


def _article_body_set(a: Article, new_body: str) -> Article:
    return Article(title=a.title, body=new_body)


def demo_focus_plan(article: Article) -> None:
    body_lens = lens(_article_body_get, _article_body_set)
    plan = focus(
        body_lens,
        sequence(task("strip_ws"), task("to_lower"), task("normalize_ws")),
    )
    report = run_structured_plan(
        plan,
        Implementation,
        input_value=article,
        aggregate_fn=None,
        choose_fn=None,
        snapshot=True,
    )
    print("[Focus] title:", report.output.title)
    print("[Focus] body:", report.output.body)


# ---------------------------------
# Demo 4: Loop + choose (argmax)
# ---------------------------------


def demo_loop_and_choose(input_text: str) -> None:
    # Loop: repeatedly strip noisy '!!' until none remain, then choose best variant by length
    def noisy(s: str) -> bool:
        return "!!" in s

    plan = sequence(
        loop_while(noisy, task("remove_noise")),
        choose(task("to_upper"), task("identity")),
    )

    report = run_structured_plan(
        plan,
        Implementation,
        input_value=input_text,
        aggregate_fn=None,
        choose_fn=argmax(lambda s: len(str(s))),
        snapshot=True,
    )
    print("[Loop+Choose] output:", report.output)


# ---------------------------------
# Utilities: write diagrams
# ---------------------------------


def write_diagrams() -> None:
    out_dir = Path("docs/diagrams")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Linear plan
    linear = Formal1(("strip_ws", "remove_noise", "normalize_ws"))
    out_dir.joinpath("Linear__plan.md").write_text("# Plan\n\n" + plan_mermaid(linear), encoding="utf-8")

    # Structured plan + trace
    plan = sequence(
        task("strip_ws"),
        parallel(task("summarize_head"), task("extract_keywords")),
        choose(task("to_upper"), task("identity")),
    )
    report = run_structured_plan(
        plan,
        Implementation,
        input_value="  Hello, Lambda-Cat!!  Agents!  ",
        aggregate_fn=concat(" | "),
        choose_fn=first(),
        snapshot=True,
    )
    out_dir.joinpath("Structured__plan.md").write_text("# Structured Plan\n\n" + structured_plan_mermaid(plan), encoding="utf-8")
    out_dir.joinpath("Structured__trace.md").write_text("# Execution Trace (Gantt)\n\n" + exec_gantt_mermaid(report), encoding="utf-8")


def _verify_functor_laws() -> None:
    quick_functor_laws(
        Implementation,
        id_name="identity",
        samples=["a", "  Hello, world!!  ", "Lambda Cat"],
        ctx=None,
    )


def main() -> None:
    sample = "  Hello, Lambda-Cat!!  AI agents, composable and typed.  "
    _verify_functor_laws()
    demo_linear_plan(sample)
    demo_structured_plan(sample)

    art = Article(title="Note", body="   A Small SAMPLE body, with   noise!!   ")
    demo_focus_plan(art)

    # AgentBuilder + convenience
    builder = AgentBuilder(Registry.mapping()).with_snapshot(True).with_evaluator(lambda s: -len(s))
    built = builder.build()
    # run_seq convenience
    report = built.run_seq("strip_ws", "normalize_ws", input_value=sample)
    print("[AgentBuilder] output:", report.output)


if __name__ == "__main__":
    main()


