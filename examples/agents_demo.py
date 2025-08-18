from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Mapping

from LambdaCat.core.presentation import Formal1
from LambdaCat.agents import (
    Agent,
    task,
    sequence,
    parallel,
    choose,
    lens,
    focus,
    run_structured_plan,
    quick_functor_laws,
)


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

def _aggregate_concat(outputs: List[str]) -> str:
    # keep type stable: concatenate branch outputs deterministically
    return " | ".join(outputs)


def _choose_first(outputs: List[str]) -> int:
    # deterministic: pick first branch
    return 0


def demo_structured_plan(input_text: str) -> None:
    plan = sequence(
        task("strip_ws"),
        task("remove_noise"),
        parallel(task("summarize_head"), task("extract_keywords")),
        choose(task("to_upper"), task("identity")),
    )

    report = run_structured_plan(
        plan,
        Implementation,
        input_value=input_text,
        aggregate_fn=_aggregate_concat,
        choose_fn=_choose_first,
        snapshot=True,
    )
    print("[Structured] output:", report.output)


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


if __name__ == "__main__":
    main()


