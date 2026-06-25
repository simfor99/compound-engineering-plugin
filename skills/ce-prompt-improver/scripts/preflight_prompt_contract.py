#!/usr/bin/env python3
"""Run deterministic preflight checks for one prompt contract or variant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prompt_preflight import build_preflight_check


def read_prompt(args: argparse.Namespace) -> str:
    parts: list[str] = []
    for file_path in args.prompt or []:
        parts.append(Path(file_path).expanduser().read_text(encoding="utf-8"))
    if args.system:
        parts.append(Path(args.system).expanduser().read_text(encoding="utf-8"))
    if args.user:
        parts.append(Path(args.user).expanduser().read_text(encoding="utf-8"))
    if args.text:
        parts.append(args.text)
    return "\n\n".join(part for part in parts if part)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run provider-fit, simplicity and anti-overfit preflight checks.")
    parser.add_argument("--prompt", action="append", help="Prompt file to inspect. Can be passed multiple times.")
    parser.add_argument("--system", help="System prompt file.")
    parser.add_argument("--user", help="User prompt file.")
    parser.add_argument("--text", help="Inline prompt text.")
    parser.add_argument("--case-id", default="")
    parser.add_argument("--variant-id", default="")
    parser.add_argument("--provider-route", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--eval-file", action="append", default=[], help="Evaluation, testset or rubric file to hash.")
    parser.add_argument("--has-train-test-split", action="store_true")
    parser.add_argument("--mutation-history", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    prompt_text = read_prompt(args)
    if not prompt_text.strip():
        raise SystemExit("No prompt text supplied.")

    report = build_preflight_check(
        prompt_text,
        case_id=args.case_id,
        variant_id=args.variant_id,
        provider_route=args.provider_route,
        model=args.model,
        eval_files=[Path(item) for item in args.eval_file],
        has_train_test_split=args.has_train_test_split,
        mutation_history_path=args.mutation_history,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded + "\n", encoding="utf-8")
        print(args.out)
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
