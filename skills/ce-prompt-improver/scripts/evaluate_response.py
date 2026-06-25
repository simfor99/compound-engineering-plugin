#!/usr/bin/env python3
"""Evaluate one CE prompt-lab provider response."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_json(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json|jsonc|text)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    first_obj = stripped.find("{")
    first_arr = stripped.find("[")
    starts = [idx for idx in (first_obj, first_arr) if idx >= 0]
    if not starts:
        raise json.JSONDecodeError("No JSON object or array found", stripped, 0)
    start = min(starts)
    opener = stripped[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(stripped)):
        ch = stripped[idx]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return json.loads(stripped[start : idx + 1])
    raise json.JSONDecodeError("No complete JSON value found", stripped, start)


def evaluate(text: str, expected_object: str | None) -> tuple[object | None, dict[str, object]]:
    parsed: object | None = None
    parse_error: str | None = None
    try:
        parsed = extract_json(text)
    except Exception as exc:  # noqa: BLE001
        parse_error = str(exc)
    schema_ok = parse_error is None
    if expected_object and isinstance(parsed, dict):
        schema_ok = expected_object in parsed
    elif expected_object:
        schema_ok = False
    return parsed, {
        "schema_ok": schema_ok,
        "parse_error": parse_error,
        "expected_object": expected_object,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--response-text", type=Path, required=True)
    parser.add_argument("--expected-object")
    parser.add_argument("--parsed-out", type=Path)
    parser.add_argument("--metrics-out", type=Path)
    args = parser.parse_args()
    parsed, metrics = evaluate(args.response_text.read_text(encoding="utf-8"), args.expected_object)
    if args.parsed_out:
        args.parsed_out.parent.mkdir(parents=True, exist_ok=True)
        args.parsed_out.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.metrics_out:
        args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0 if metrics["parse_error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
