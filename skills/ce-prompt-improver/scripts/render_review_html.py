#!/usr/bin/env python3
"""Render the shared static Prompt A/B review HTML from a data.json packet."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_shared_renderer() -> Path:
    skills_root = Path(__file__).resolve().parents[2]
    candidates = [
        skills_root / "shared" / "scripts" / "render_prompt_ab_review_surface.py",
        Path.home() / ".codex" / "skills" / "shared" / "scripts" / "render_prompt_ab_review_surface.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("shared static renderer not found in ~/.codex/skills/shared or plugin-local shared skill")


def default_out(data_path: Path) -> Path:
    if data_path.name != "data.json" or data_path.parent.name != "assets" or data_path.parent.parent.name != "html":
        raise ValueError("data path must end with html/assets/data.json")
    return data_path.parent.parent / "index.html"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path, help="Path to html/assets/data.json")
    parser.add_argument("--out", type=Path, help="Path to rendered html/index.html")
    parser.add_argument("--template", type=Path, help="Optional template override")
    args = parser.parse_args()

    data = args.data.expanduser().resolve()
    out = (args.out.expanduser().resolve() if args.out else default_out(data))
    if not data.exists():
        raise SystemExit(f"data.json not found: {data}")
    try:
        shared_renderer = find_shared_renderer()
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    command = [
        sys.executable,
        str(shared_renderer),
        "--data",
        str(data),
        "--out",
        str(out),
    ]
    if args.template:
        command.extend(["--template", str(args.template.expanduser().resolve())])
    try:
        subprocess.run(command, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        details = "\n".join(part for part in [exc.stdout, exc.stderr] if part)
        raise SystemExit(f"static review renderer failed: {details.strip() or exc}") from exc
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
