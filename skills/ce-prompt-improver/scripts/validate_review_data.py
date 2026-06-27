#!/usr/bin/env python3
"""Validate CE Prompt Improver PromptReview data before rendering static HTML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STATIC_EVIDENCE_CLASSES = {
    "static_mock",
    "layout_smoke",
    "layout_smoke_not_ab_test",
}

KNOWN_EVIDENCE_CLASSES = {
    "static_mock",
    "layout_smoke",
    "layout_smoke_not_ab_test",
    "artifact_replay",
    "unit_mocked",
    "integration_local",
    "live_local",
    "production_like",
    "manual_user_verified",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def issue(issues: list[dict[str, str]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


def validate(data: dict[str, Any], data_path: Path | None = None, require_real_ab: bool = False) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    evidence_class = str(data.get("evidenceClass") or "")
    if not evidence_class:
        issue(issues, "evidenceClass", "must be a non-empty evidence label")
    if require_real_ab and evidence_class in STATIC_EVIDENCE_CLASSES:
        issue(issues, "evidenceClass", "real A/B tests require provider or replay evidence, not a layout/static mock")

    variants = data.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        issue(issues, "variants", "must contain at least baseline and candidate")
        variant_ids: set[str] = set()
    else:
        variant_ids = {str(item.get("id")) for item in variants if isinstance(item, dict) and item.get("id")}
        if len(variant_ids) != len(variants):
            issue(issues, "variants", "each variant must have a unique id")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        issue(issues, "cases", "must contain at least one case")
    else:
        for case_index, case in enumerate(cases):
            if not isinstance(case, dict):
                issue(issues, f"cases[{case_index}]", "case must be object")
                continue
            case_id = str(case.get("id") or f"case-{case_index}")
            results = case.get("results")
            if not isinstance(results, list) or len(results) < 2:
                issue(issues, f"cases[{case_id}].results", "must contain at least two variant results")
                continue
            seen: set[str] = set()
            for result_index, result in enumerate(results):
                if not isinstance(result, dict):
                    issue(issues, f"cases[{case_id}].results[{result_index}]", "result must be object")
                    continue
                variant_id = str(result.get("variantId") or "")
                seen.add(variant_id)
                if variant_id not in variant_ids:
                    issue(issues, f"cases[{case_id}].results[{result_index}].variantId", "unknown variant")
                if "parsedOk" not in result:
                    issue(issues, f"cases[{case_id}].results[{result_index}].parsedOk", "missing parsedOk")
                metrics = result.get("metrics")
                if not isinstance(metrics, dict):
                    issue(issues, f"cases[{case_id}].results[{result_index}].metrics", "missing metrics object")
                elif result.get("parsedOk") and "schema_ok" not in metrics:
                    issue(issues, f"cases[{case_id}].results[{result_index}].metrics.schema_ok", "missing schema_ok")
                if "prompt" not in result:
                    issue(issues, f"cases[{case_id}].results[{result_index}].prompt", "missing prompt")
                if "parsedOutput" not in result:
                    issue(issues, f"cases[{case_id}].results[{result_index}].parsedOutput", "missing parsedOutput")
                if require_real_ab:
                    provider_route = str(result.get("providerRoute") or "")
                    model = str(result.get("model") or "")
                    if provider_route in {"", "static_mock", "layout_smoke", "layout_smoke_not_ab_test", "fixture"}:
                        issue(issues, f"cases[{case_id}].results[{result_index}].providerRoute", "real A/B tests need a real provider route or artifact replay route")
                    if model in {"", "not_called"}:
                        issue(issues, f"cases[{case_id}].results[{result_index}].model", "real A/B tests need a recorded model")
                    if result.get("durationMs") is None:
                        issue(issues, f"cases[{case_id}].results[{result_index}].durationMs", "real A/B tests need recorded runtime duration")
                    if not result.get("providerCalledAt"):
                        issue(issues, f"cases[{case_id}].results[{result_index}].providerCalledAt", "real A/B tests need the provider run date/time")
                    if not (result.get("artifactBase") or result.get("artifact_base")):
                        issue(issues, f"cases[{case_id}].results[{result_index}].artifactBase", "real A/B tests need artifactBase trace pointers")
            if variant_ids and not variant_ids.issubset(seen):
                issue(issues, f"cases[{case_id}].results", "missing one or more variant results")

    if evidence_class in STATIC_EVIDENCE_CLASSES:
        text = json.dumps(data, ensure_ascii=False).lower()
        risky = ["provider_run_complete", "production_ready", "deployed", "customer_api_ready", "real_ab_test"]
        for token in risky:
            if token in text and token != evidence_class.lower():
                issue(issues, "layout_or_static.claims", f"layout/static evidence must not claim {token}")

    if data_path:
        parts = data_path.parts
        if data_path.name != "data.json" or len(parts) < 3 or parts[-3:] != ("html", "assets", "data.json"):
            issue(issues, "path", "static review data must end with html/assets/data.json")

    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "case_count": len(cases) if isinstance(cases, list) else 0,
        "variant_count": len(variants) if isinstance(variants, list) else 0,
        "evidenceClass": evidence_class,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--require-real-ab", action="store_true")
    args = parser.parse_args()

    report = validate(load_json(args.data), args.data, require_real_ab=args.require_real_ab)
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
