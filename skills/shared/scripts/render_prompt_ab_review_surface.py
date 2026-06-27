#!/usr/bin/env python3
"""Render the shared Prompt A/B review surface from a JSON data file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PLACEHOLDER = "__PROMPT_AB_REVIEW_DATA_JSON__"
DEFAULT_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "openspec-prompt-improver"
    / "index.template.html"
)


def render(data_path: Path, out_path: Path, template_path: Path = DEFAULT_TEMPLATE) -> None:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"Template placeholder missing: {PLACEHOLDER}")

    rendered = template.replace(
        PLACEHOLDER,
        json.dumps(data, ensure_ascii=False, indent=2),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to review-surface data.json")
    parser.add_argument("--out", required=True, help="Path to rendered index.html")
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE),
        help="Override HTML template path",
    )
    args = parser.parse_args()

    render(Path(args.data), Path(args.out), Path(args.template))
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
