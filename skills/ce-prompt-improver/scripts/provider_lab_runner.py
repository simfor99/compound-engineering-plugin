#!/usr/bin/env python3
"""Run one CE prompt-lab variant through a real provider or labeled fixture."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_response import evaluate  # noqa: E402


PERPLEXITY_AGENT_URL = "https://api.perplexity.ai/v1/agent"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def load_json(path: Path | None) -> dict[str, object]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def stringify(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def render_template(text: str, variables: dict[str, object]) -> str:
    rendered = text
    for key, value in variables.items():
        rendered = rendered.replace(f"${key}", stringify(value))
    return rendered


def response_text_from_agent(raw: dict[str, object]) -> str:
    output = raw.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for piece in content:
                    if isinstance(piece, dict) and isinstance(piece.get("text"), str):
                        chunks.append(piece["text"])
            elif isinstance(content, str):
                chunks.append(content)
        if chunks:
            return "\n".join(chunks)
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
    if isinstance(raw.get("text"), str):
        return str(raw["text"])
    return json.dumps(raw, ensure_ascii=False, indent=2)


def call_perplexity_agent(request_body: dict[str, object]) -> dict[str, object]:
    api_key = os.environ.get("PERPLEXITY_API_KEY") or os.environ.get("VITE_PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY or VITE_PERPLEXITY_API_KEY is required for real provider runs.")
    request = urllib.request.Request(
        PERPLEXITY_AGENT_URL,
        data=json.dumps(request_body).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Perplexity Agent API error {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--variant-id", required=True)
    parser.add_argument("--variant-label")
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--user", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--surface", choices=["perplexity-agent", "fixture"], default="fixture")
    parser.add_argument("--fixture-response", type=Path)
    parser.add_argument("--preset", default="pro-search")
    parser.add_argument("--max-output-tokens", type=int, default=1200)
    parser.add_argument("--domain-filter", action="append", default=[])
    parser.add_argument("--expected-object")
    parser.add_argument("--env-file", type=Path, default=Path(".env.local"))
    args = parser.parse_args()

    load_env_file(args.env_file)

    case = load_json(args.case)
    variables: dict[str, object] = {}
    if isinstance(case.get("variables"), dict):
        variables.update(case["variables"])  # type: ignore[arg-type]
    variables.update({key: value for key, value in case.items() if key != "variables"})
    case_id = str(case.get("id") or case.get("case_id") or "case")
    company = str(case.get("companyName") or case.get("company_name") or case_id)
    safe_base = f"{case_id}__{args.variant_id}"
    artifact_base = args.out_dir / safe_base
    args.out_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = render_template(args.system.read_text(encoding="utf-8"), variables)
    user_prompt = render_template(args.user.read_text(encoding="utf-8"), variables)
    rendered_prompt = f"{system_prompt.rstrip()}\n\n{user_prompt.rstrip()}\n"

    request_without_secret: dict[str, object] = {
        "preset": args.preset,
        "input": rendered_prompt,
        "max_output_tokens": args.max_output_tokens,
    }
    if args.domain_filter:
        request_without_secret["tools"] = [
            {"type": "web_search", "filters": {"search_domain_filter": args.domain_filter}}
        ]

    started = time.time()
    error: str | None = None
    if args.surface == "fixture":
        if not args.fixture_response:
            raise SystemExit("--fixture-response is required for fixture runs")
        response_text = args.fixture_response.read_text(encoding="utf-8")
        raw_response: dict[str, object] = {"fixture": True, "response_text": response_text, "request": request_without_secret}
        model = "fixture"
        token_usage = None
    else:
        try:
            raw_response = call_perplexity_agent(request_without_secret)
            response_text = response_text_from_agent(raw_response)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            raw_response = {"error": error, "request": request_without_secret}
            response_text = ""
        model = str(raw_response.get("model") or "perplexity-agent")
        token_usage = raw_response.get("usage") if isinstance(raw_response.get("usage"), dict) else None

    duration_ms = int((time.time() - started) * 1000)
    parsed, metrics = evaluate(response_text, args.expected_object)
    metrics.update({
        "duration_ms": duration_ms,
        "model": model,
        "token_usage": token_usage,
        "provider_error": error,
        "case_id": case_id,
        "variant_id": args.variant_id,
    })

    artifact_base.with_name(artifact_base.name + "__01_request.json").write_text(json.dumps(request_without_secret, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifact_base.with_name(artifact_base.name + "__02_rendered-prompt.txt").write_text(rendered_prompt, encoding="utf-8")
    artifact_base.with_name(artifact_base.name + "__03_raw-response.json").write_text(json.dumps(raw_response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifact_base.with_name(artifact_base.name + "__04_response-text.txt").write_text(response_text, encoding="utf-8")
    artifact_base.with_name(artifact_base.name + "__05_parsed-output.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifact_base.with_name(artifact_base.name + "__06_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "case_id": case_id,
        "company_name": company,
        "variant_id": args.variant_id,
        "variant_label": args.variant_label or args.variant_id,
        "provider_route": args.surface,
        "model": model,
        "token_usage": token_usage,
        "max_output_tokens": args.max_output_tokens,
        "prompt": {"system": system_prompt, "user": user_prompt},
        "duration_ms": duration_ms,
        "error": error,
        "response_text": response_text,
        "parsed_ok": metrics["parse_error"] is None,
        "parsed_output": parsed,
        "parse_error": metrics["parse_error"],
        "metrics": metrics,
        "artifact_base": str(artifact_base),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
