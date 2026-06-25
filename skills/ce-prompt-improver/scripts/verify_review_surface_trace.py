#!/usr/bin/env python3
"""Verify that review-surface data mirrors the lab-runner artifact trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ARTIFACT_SUFFIXES = {
    "request": "__01_request.json",
    "rendered_prompt": "__02_rendered-prompt.txt",
    "raw_response": "__03_raw-response.json",
    "response_text": "__04_response-text.txt",
    "parsed_output": "__05_parsed-output.json",
    "metrics": "__06_metrics.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_artifact_base(raw: str, results_path: Path) -> Path:
    base = Path(raw)
    candidates = [base]
    if not base.is_absolute():
        candidates.extend([
            results_path.parent / base,
            results_path.parent.parent / base,
            Path.cwd() / base,
        ])
    for candidate in candidates:
        prompt_file = candidate.with_name(candidate.name + ARTIFACT_SUFFIXES["rendered_prompt"])
        if prompt_file.exists():
            return candidate
    return base


def split_rendered_prompt(text: str) -> dict[str, str]:
    system, separator, user = text.partition("\n\n")
    if not separator:
        return {"system": "", "user": text}
    return {"system": system.rstrip(), "user": user.rstrip()}


def summary_prompt_parts(item: dict[str, Any]) -> dict[str, str] | None:
    prompt = item.get("prompt")
    if isinstance(prompt, dict):
        system = prompt.get("system")
        user = prompt.get("user")
        if isinstance(system, str) and isinstance(user, str):
            return {"system": system, "user": user}
    return None


def prompt_recomposes_rendered(prompt: dict[str, str] | None, rendered: str) -> bool:
    if not prompt:
        return False
    return f"{prompt['system'].rstrip()}\n\n{prompt['user'].rstrip()}".rstrip() == rendered.rstrip()


def expected_prompt_parts(item: dict[str, Any], rendered: str) -> dict[str, str]:
    summary_prompt = summary_prompt_parts(item)
    if prompt_recomposes_rendered(summary_prompt, rendered):
        return summary_prompt  # type: ignore[return-value]
    return split_rendered_prompt(rendered)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def data_result_index(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index = {}
    for case in data.get("cases", []):
        case_id = str(case.get("id", ""))
        for result in case.get("results", []):
            index[(case_id, str(result.get("variantId", "")))] = result
    return index


def add_issue(issues: list[dict[str, str]], case_id: str, variant_id: str, field: str, message: str) -> None:
    issues.append({
        "case_id": case_id,
        "variant_id": variant_id,
        "field": field,
        "message": message,
    })


def verify(results_path: Path, data_path: Path | None) -> dict[str, Any]:
    summary = load_json(results_path)
    data = load_json(data_path) if data_path else None
    data_index = data_result_index(data) if isinstance(data, dict) else {}
    issues: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []

    for item in summary.get("results", []):
        case_id = str(item.get("case_id") or item.get("caseId") or "")
        variant_id = str(item.get("variant_id") or item.get("variantId") or "")
        raw_base = item.get("artifact_base") or item.get("artifactBase")
        if not isinstance(raw_base, str) or not raw_base:
            add_issue(issues, case_id, variant_id, "artifact_base", "missing artifact base")
            continue

        base = resolve_artifact_base(raw_base, results_path)
        paths = {key: base.with_name(base.name + suffix) for key, suffix in ARTIFACT_SUFFIXES.items()}
        missing = [key for key, path in paths.items() if not path.exists()]
        for key in missing:
            add_issue(issues, case_id, variant_id, key, f"missing artifact file: {paths[key]}")
        if missing:
            continue

        request = load_json(paths["request"])
        raw_response = load_json(paths["raw_response"])
        parsed_output = load_json(paths["parsed_output"])
        metrics = load_json(paths["metrics"])
        rendered_prompt = paths["rendered_prompt"].read_text(encoding="utf-8")
        response_text = paths["response_text"].read_text(encoding="utf-8")
        split_prompt = expected_prompt_parts(item, rendered_prompt)
        summary_prompt = summary_prompt_parts(item)

        if request.get("input") != rendered_prompt:
            add_issue(issues, case_id, variant_id, "request.input", "request input does not match rendered prompt artifact")
        if summary_prompt and not prompt_recomposes_rendered(summary_prompt, rendered_prompt):
            if summary_prompt["system"] != split_prompt["system"]:
                add_issue(issues, case_id, variant_id, "summary.prompt.system", "summary system prompt differs from rendered prompt artifact")
            if summary_prompt["user"] != split_prompt["user"]:
                add_issue(issues, case_id, variant_id, "summary.prompt.user", "summary user prompt differs from rendered prompt artifact")
        raw_request = raw_response.get("request") if isinstance(raw_response, dict) else None
        if isinstance(raw_request, dict) and canonical(raw_request) != canonical(request):
            add_issue(issues, case_id, variant_id, "raw_response.request", "raw response embedded request differs from request artifact")
        if item.get("response_text") != response_text:
            add_issue(issues, case_id, variant_id, "summary.response_text", "summary response_text differs from response text artifact")
        if canonical(item.get("parsed_output")) != canonical(parsed_output):
            add_issue(issues, case_id, variant_id, "summary.parsed_output", "summary parsed_output differs from parsed output artifact")
        if canonical(item.get("metrics")) != canonical(metrics):
            add_issue(issues, case_id, variant_id, "summary.metrics", "summary metrics differ from metrics artifact")

        surface = data_index.get((case_id, variant_id))
        if data_path and not surface:
            add_issue(issues, case_id, variant_id, "data.result", "data.json result missing")
        if surface:
            prompt = surface.get("prompt") if isinstance(surface.get("prompt"), dict) else {}
            if prompt.get("system") != split_prompt["system"]:
                add_issue(issues, case_id, variant_id, "data.prompt.system", "surface system prompt differs from rendered prompt artifact")
            if prompt.get("user") != split_prompt["user"]:
                add_issue(issues, case_id, variant_id, "data.prompt.user", "surface user prompt differs from rendered prompt artifact")
            if surface.get("responseText") != response_text:
                add_issue(issues, case_id, variant_id, "data.responseText", "surface responseText differs from response text artifact")
            if canonical(surface.get("parsedOutput")) != canonical(parsed_output):
                add_issue(issues, case_id, variant_id, "data.parsedOutput", "surface parsedOutput differs from parsed output artifact")
            if canonical(surface.get("metrics")) != canonical(metrics):
                add_issue(issues, case_id, variant_id, "data.metrics", "surface metrics differ from metrics artifact")

        rows.append({
            "case_id": case_id,
            "variant_id": variant_id,
            "artifact_base": str(base),
            "hashes": {key: sha256_file(path) for key, path in paths.items()},
            "request_input_matches_rendered_prompt": request.get("input") == rendered_prompt,
            "surface_checked": bool(surface),
        })

    return {
        "status": "pass" if not issues else "fail",
        "results_path": str(results_path),
        "data_path": str(data_path) if data_path else None,
        "checked_results": len(rows),
        "issues": issues,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = verify(args.results, args.data)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
