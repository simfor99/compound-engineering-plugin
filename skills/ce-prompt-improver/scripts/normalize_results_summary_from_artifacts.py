#!/usr/bin/env python3
"""Normalize a results-summary JSON from its lab-runner artifact files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUFFIXES = {
    "request": "__01_request.json",
    "rendered_prompt": "__02_rendered-prompt.txt",
    "raw_response": "__03_raw-response.json",
    "response_text": "__04_response-text.txt",
    "parsed_output": "__05_parsed-output.json",
    "metrics": "__06_metrics.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_base(raw: str, summary_path: Path) -> Path:
    base = Path(raw)
    candidates = [base]
    if not base.is_absolute():
        candidates.extend([summary_path.parent / base, summary_path.parent.parent / base, Path.cwd() / base])
    for candidate in candidates:
        if candidate.with_name(candidate.name + SUFFIXES["rendered_prompt"]).exists():
            return candidate
    return base


def split_rendered_prompt(text: str) -> dict[str, str]:
    system, separator, user = text.partition("\n\n")
    if not separator:
        return {"system": "", "user": text.rstrip()}
    return {"system": system.rstrip(), "user": user.rstrip()}


def prompt_recomposes_rendered(prompt: Any, rendered: str) -> bool:
    if not isinstance(prompt, dict):
        return False
    system = prompt.get("system")
    user = prompt.get("user")
    if not isinstance(system, str) or not isinstance(user, str):
        return False
    return f"{system.rstrip()}\n\n{user.rstrip()}".rstrip() == rendered.rstrip()


def normalize(summary: dict[str, Any], summary_path: Path) -> dict[str, Any]:
    for item in summary.get("results", []):
        if not isinstance(item, dict):
            continue
        raw_base = item.get("artifact_base") or item.get("artifactBase")
        if not isinstance(raw_base, str) or not raw_base:
            continue
        base = resolve_base(raw_base, summary_path)
        paths = {key: base.with_name(base.name + suffix) for key, suffix in SUFFIXES.items()}
        if paths["rendered_prompt"].exists():
            rendered_prompt = paths["rendered_prompt"].read_text(encoding="utf-8")
            if not prompt_recomposes_rendered(item.get("prompt"), rendered_prompt):
                item["prompt"] = split_rendered_prompt(rendered_prompt)
        if paths["response_text"].exists():
            item["response_text"] = paths["response_text"].read_text(encoding="utf-8")
        if paths["parsed_output"].exists():
            item["parsed_output"] = load_json(paths["parsed_output"])
        if paths["metrics"].exists():
            metrics = load_json(paths["metrics"])
            item["metrics"] = metrics
            if isinstance(metrics, dict):
                if "duration_ms" in metrics:
                    item["duration_ms"] = metrics["duration_ms"]
                if "parse_error" in metrics:
                    item["parse_error"] = metrics["parse_error"]
                    item["parsed_ok"] = metrics["parse_error"] is None
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    summary = load_json(args.results)
    if not isinstance(summary, dict):
        raise SystemExit("results summary must be a JSON object")
    normalized = normalize(summary, args.results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
