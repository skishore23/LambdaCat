"""Command-line interface for LambdaCat."""

import argparse
import json
import sys
from typing import Optional

from .core import (
    APPLICATIVE_SUITE,
    CATEGORY_SUITE,
    FUNCTOR_SUITE,
    MONAD_SUITE,
    Diagram,
    discrete,
    run_suite,
    simplex,
    terminal_category,
    walking_isomorphism,
)
from .core.fp.instances.identity import Id
from .core.fp.instances.option import Option
from .core.fp.instances.result import Result


def cmd_laws(args: argparse.Namespace) -> int:
    """Run law tests for a specific suite."""
    suites = {
        "category": CATEGORY_SUITE,
        "functor": FUNCTOR_SUITE,
        "applicative": APPLICATIVE_SUITE,
        "monad": MONAD_SUITE,
    }

    suite = suites.get(args.suite)
    if not suite:
        print(f"Error: Unknown suite '{args.suite}'", file=sys.stderr)
        print(f"Available suites: {', '.join(suites.keys())}", file=sys.stderr)
        return 1

    if args.suite == "category":
        categories = {
            "simplex(2)": simplex(2),
            "discrete(['A', 'B'])": discrete(['A', 'B']),
            "walking_isomorphism": walking_isomorphism(),
            "terminal": terminal_category(),
        }

        results = {}
        all_passed = True

        for name, cat in categories.items():
            report = run_suite(cat, suite)
            results[name] = {
                "passed": report.ok,
                "total_laws": len(report.results),
                "failed_laws": [lr.law.name for lr in report.results if not lr.passed],
                "violations": sum(len(lr.violations) for lr in report.results),
            }
            if not report.ok:
                all_passed = False

    else:
        instances = {
            "Option": Option,
            "Result": Result,
            "Id": Id,
        }

        results = {}
        all_passed = True

        for name, instance in instances.items():
            try:
                report = run_suite(instance, suite)
                results[name] = {
                    "passed": report.ok,
                    "total_laws": len(report.results),
                    "failed_laws": [lr.law.name for lr in report.results if not lr.passed],
                    "violations": sum(len(lr.violations) for lr in report.results),
                }
                if not report.ok:
                    all_passed = False
            except Exception as e:
                results[name] = {"error": str(e)}

    if args.format == "json":
        output = {
            "suite": args.suite,
            "passed": all_passed,
            "results": results,
        }
        print(json.dumps(output, indent=2))
    else:
        # Text format
        print(f"🧪 LambdaCat {args.suite.title()} Laws Report")
        print("=" * 50)

        for name, result in results.items():
            if "error" in result:
                print(f"\n❌ {name}: {result['error']}")
            elif result["passed"]:
                print(f"\n✅ {name}: ALL LAWS PASSED ({result['total_laws']} laws)")
            else:
                print(f"\n❌ {name}: FAILED")
                print(f"   Failed laws: {', '.join(result['failed_laws'])}")
                print(f"   Total violations: {result['violations']}")

        print("\n" + "=" * 50)
        if all_passed:
            print("✅ Overall: ALL TESTS PASSED")
        else:
            print("❌ Overall: SOME TESTS FAILED")

    return 0 if all_passed else 1


def cmd_render(args: argparse.Namespace) -> int:
    """Render a category or diagram."""
    # For demo, create a simple category
    if args.example:
        if args.example == "simplex":
            simplex(2)
            diagram = Diagram.from_edges(
                ["0", "1", "2"],
                [("0", "1", "0->1"), ("1", "2", "1->2"), ("0", "2", "0->2")]
            )
        elif args.example == "iso":
            walking_isomorphism()
            diagram = Diagram.from_edges(
                ["A", "B"],
                [("A", "B", "f"), ("B", "A", "g")]
            )
        else:
            print(f"Error: Unknown example '{args.example}'", file=sys.stderr)
            print("Available examples: simplex, iso", file=sys.stderr)
            return 1
    else:
        # In a real implementation, we'd load from a file
        print("Error: Please specify --example for demo", file=sys.stderr)
        return 1

    # Render based on format
    if args.format == "mermaid":
        output = diagram.to_mermaid()
    elif args.format == "dot":
        output = diagram.to_dot()
    else:
        print(f"Error: Unknown format '{args.format}'", file=sys.stderr)
        return 1

    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Rendered to {args.output}")
    else:
        print(output)

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="lambdacat",
        description="LambdaCat - Composable agents on a typed categorical core"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Laws command
    laws_parser = subparsers.add_parser("laws", help="Run law tests")
    laws_parser.add_argument(
        "--suite",
        choices=["category", "functor", "applicative", "monad"],
        required=True,
        help="Which law suite to run"
    )
    laws_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)"
    )

    # Render command
    render_parser = subparsers.add_parser("render", help="Render categories/diagrams")
    render_parser.add_argument(
        "--format",
        choices=["mermaid", "dot"],
        required=True,
        help="Output format"
    )
    render_parser.add_argument(
        "--example",
        choices=["simplex", "iso"],
        help="Render a built-in example"
    )
    render_parser.add_argument(
        "--output", "-o",
        help="Output file (default: stdout)"
    )

    # Parse arguments
    args = parser.parse_args(argv)

    # Dispatch to command
    if args.command == "laws":
        return cmd_laws(args)
    elif args.command == "render":
        return cmd_render(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
