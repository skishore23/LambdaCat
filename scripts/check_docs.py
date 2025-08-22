from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterator


CODE_BLOCK_RE = re.compile(r"```python\n(.*?)\n```", re.DOTALL)


def iter_python_blocks(md_text: str) -> Iterator[str]:
    for m in CODE_BLOCK_RE.finditer(md_text):
        yield m.group(1)


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for i, block in enumerate(iter_python_blocks(text), start=1):
        # Isolated namespace per block
        ns: dict[str, object] = {}
        try:
            exec(block, ns, ns)
        except Exception as e:
            errors.append(f"{path.name} block#{i}: {e}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default=str(Path(__file__).parents[1] / "docs"))
    args = parser.parse_args()
    docs_dir = Path(args.docs_dir)
    failures: list[str] = []
    for p in sorted(docs_dir.glob("*.md")):
        failures.extend(check_file(p))
    if failures:
        print("Docs code blocks failed:")
        for f in failures:
            print(" -", f)
        raise SystemExit(1)
    print("All docs code blocks executed successfully.")


if __name__ == "__main__":
    main()


