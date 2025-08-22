from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from LambdaCat.agents.actions import Task, choose, focus, loop_while, parallel, sequence
from LambdaCat.agents.runtime import compile_plan, compile_to_kleisli
from LambdaCat.core.fp.instances.option import Option
from LambdaCat.core.optics import Lens

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
# Demo 1: Linear plan comparison
# -----------------------------

def demo_linear_plan(input_text: str) -> None:
    # Create two different plans
    plan_a = sequence(Task("strip_ws"), Task("remove_noise"), Task("normalize_ws"))
    plan_b = sequence(Task("strip_ws"), Task("to_lower"), Task("normalize_ws"))

    # Execute both plans and compare results
    executable_a = compile_plan(Implementation, plan_a)
    executable_b = compile_plan(Implementation, plan_b)

    result_a = executable_a(input_text)
    result_b = executable_b(input_text)

    # Choose the shorter result (simple heuristic)
    if len(result_a) <= len(result_b):
        chosen_plan = "Plan A"
        chosen_result = result_a
    else:
        chosen_plan = "Plan B"
        chosen_result = result_b

    print(f"[Linear] chosen: {chosen_plan}")
    print(f"[Linear] output: {chosen_result}")
    print(f"[Linear] Plan A result: {result_a}")
    print(f"[Linear] Plan B result: {result_b}")


# ---------------------------------------------
# Demo 2: Structured plan (parallel + choose)
# ---------------------------------------------

def demo_structured_plan(input_text: str) -> None:
    # Create a complex plan with parallel and choice operations
    plan = sequence(
        Task("strip_ws"),
        Task("remove_noise"),
        parallel(Task("summarize_head"), Task("extract_keywords")),
        choose(Task("to_upper"), Task("identity")),
    )

    # Execute the plan with aggregation for parallel results
    def aggregate_parallel(results):
        return " | ".join(str(r) for r in results)

    def choose_first(results):
        return 0 if results else 0  # Return index, not the result itself

    executable = compile_plan(Implementation, plan,
                            aggregate_fn=aggregate_parallel,
                            choose_fn=choose_first)
    result = executable(input_text)

    print(f"[Structured] output: {result}")

    # Also demonstrate Kleisli compilation
    kleisli_plan = compile_to_kleisli(Implementation, plan, Option)
    kleisli_result = kleisli_plan(input_text)
    print(f"[Structured] Kleisli result: {kleisli_result}")


# ---------------------------------
# Demo 3: Lens focus on nested state
# ---------------------------------

@dataclass(frozen=True)
class Article:
    title: str
    body: str


def demo_focus_plan(article: Article) -> None:
    # Create a lens for the article body
    body_lens = Lens(
        get=lambda a: a.body,
        set=lambda new_body, a: Article(title=a.title, body=new_body)
    )

    # Create a plan that focuses on the body
    body_processing_plan = sequence(
        Task("strip_ws"),
        Task("to_lower"),
        Task("normalize_ws")
    )

    plan = focus(body_lens, body_processing_plan)

    # Execute the focused plan
    executable = compile_plan(Implementation, plan)
    result = executable(article)

    print(f"[Focus] Original title: {article.title}")
    print(f"[Focus] Original body: '{article.body}'")
    if hasattr(result, 'title') and hasattr(result, 'body'):
        print(f"[Focus] Processed title: {result.title}")
        print(f"[Focus] Processed body: '{result.body}'")
    else:
        print(f"[Focus] Focus result: {result}")
        print("[Focus] Note: Focus operation may need adjustment for this lens implementation")


# ---------------------------------
# Demo 4: Loop + choose
# ---------------------------------

def demo_loop_and_choose(input_text: str) -> None:
    # Loop: repeatedly strip noisy '!!' until none remain, then choose best variant by length
    def has_noise(s: str) -> bool:
        return "!!" in s

    plan = sequence(
        loop_while(has_noise, Task("remove_noise")),
        choose(Task("to_upper"), Task("identity")),
    )

    # Choose the longer result (argmax by length)
    def choose_longest(results):
        if not results:
            return 0
        return max(range(len(results)), key=lambda i: len(str(results[i])))

    executable = compile_plan(Implementation, plan, choose_fn=choose_longest)
    result = executable(input_text)

    print(f"[Loop+Choose] input: {input_text}")
    print(f"[Loop+Choose] output: {result}")


# ---------------------------------
# Demo 5: Simple sequential execution
# ---------------------------------

def demo_simple_execution() -> None:
    """Demonstrate simple sequential plan execution."""
    plan = sequence(
        Task("strip_ws"),
        Task("to_lower"),
        Task("normalize_ws")
    )

    executable = compile_plan(Implementation, plan)
    sample = "  HELLO, World!!  "
    result = executable(sample)

    print(f"[Simple] input: '{sample}'")
    print(f"[Simple] output: '{result}'")


def main() -> None:
    """Run all agent demos."""
    print("🤖 LambdaCat Agent Framework Demo")
    print("=" * 40)

    sample = "  Hello, Lambda-Cat!!  AI agents, composable and typed.  "

    print("\n1. Simple Sequential Execution:")
    demo_simple_execution()

    print("\n2. Linear Plan Comparison:")
    demo_linear_plan(sample)

    print("\n3. Structured Plan (Parallel + Choose):")
    demo_structured_plan(sample)

    print("\n4. Focus with Lenses:")
    art = Article(title="Note", body="   A Small SAMPLE body, with   noise!!   ")
    demo_focus_plan(art)

    print("\n5. Loop + Choose:")
    noisy_sample = "  Hello!! Lambda-Cat!! with noise!!  "
    demo_loop_and_choose(noisy_sample)

    print("\n🎉 All agent demos completed successfully!")


if __name__ == "__main__":
    main()


