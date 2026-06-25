#!/usr/bin/env python3
"""Print a local React PromptReview URL for a route-allowed data.json."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("--base-url", default="http://localhost:3000/app/review/prompt-ab")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    data = args.data.resolve()
    repo_root = args.repo_root.resolve()
    docs_todo = repo_root / "docs" / "todo"
    try:
        rel_to_docs_todo = data.relative_to(docs_todo)
    except ValueError as exc:
        raise SystemExit("data.json is not under docs/todo; current React resolver will reject it") from exc
    if rel_to_docs_todo.parts[-3:] != ("html", "assets", "data.json"):
        raise SystemExit("data path must end with html/assets/data.json")

    relative = data.relative_to(repo_root).as_posix()
    print(f"{args.base_url}?path={quote(relative, safe='')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
