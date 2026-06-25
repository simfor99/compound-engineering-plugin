#!/usr/bin/env python3
"""Build PromptReview-compatible data.json from CE prompt-lab round-results."""

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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def normalize_result(case_id: str, result: dict[str, Any], variants: dict[str, dict[str, Any]]) -> dict[str, Any]:
    variant_id = str(result.get("variantId") or result.get("variant_id") or "")
    require(variant_id in variants, f"Unknown variantId for case {case_id}: {variant_id}")
    parsed_ok = bool(result.get("parsedOk", result.get("parsed_ok", False)))
    metrics = dict(result.get("metrics") or {})
    metrics.setdefault("schema_ok", bool(metrics.get("schema_ok", parsed_ok)))
    return {
        "caseId": case_id,
        "variantId": variant_id,
        "variantLabel": result.get("variantLabel") or variants[variant_id].get("label") or variant_id,
        "variantShortLabel": result.get("variantShortLabel") or variants[variant_id].get("shortLabel") or variant_id[:1].upper(),
        "providerRoute": result.get("providerRoute") or result.get("provider_route") or "manual_lab",
        "providerDisplayName": result.get("providerDisplayName") or result.get("provider_display_name") or "Manual Lab",
        "model": result.get("model") or "not_called",
        "tokenUsage": result.get("tokenUsage") or result.get("token_usage"),
        "maxOutputTokens": result.get("maxOutputTokens") or result.get("max_output_tokens"),
        "durationMs": result.get("durationMs"),
        "parsedOk": parsed_ok,
        "metrics": metrics,
        "prompt": result.get("prompt") or {"system": "", "user": ""},
        "responseText": result.get("responseText") or result.get("response_text") or "",
        "parsedOutput": result.get("parsedOutput") if "parsedOutput" in result else result.get("parsed_output"),
        "artifactBase": result.get("artifactBase") or result.get("artifact_base"),
        "trace": result.get("trace") or {},
    }


def build(round_results: dict[str, Any]) -> dict[str, Any]:
    evidence_class = str(round_results.get("evidence_class") or "")
    require(bool(evidence_class), "round-results must contain evidence_class")

    variants = round_results.get("variants")
    require(isinstance(variants, list) and len(variants) >= 2, "round-results must contain at least two variants")
    variant_index = {str(variant.get("id")): variant for variant in variants if isinstance(variant, dict)}
    require(len(variant_index) == len(variants), "Each variant must have a unique id")

    cases = []
    for case in round_results.get("cases", []):
        require(isinstance(case, dict), "Each case must be an object")
        case_id = str(case.get("id") or "")
        require(case_id, "Each case must have id")
        results = case.get("results")
        require(isinstance(results, list) and len(results) >= 2, f"Case {case_id} must have at least two results")
        seen = {str(item.get("variantId") or item.get("variant_id") or "") for item in results if isinstance(item, dict)}
        require(set(variant_index).issubset(seen), f"Case {case_id} is missing one or more variant results")
        cases.append(
            {
                "id": case_id,
                "companyName": case.get("companyName") or case.get("title") or case_id,
                "testIntent": case.get("testIntent")
                or {
                    "label": case.get("label") or case_id,
                    "intent": case.get("intent") or "",
                    "expected_behavior": case.get("expected_behavior") or case.get("expectedBehavior") or "",
                    "watch_for": case.get("watch_for") or case.get("watchFor") or "",
                },
                "metadata": case.get("metadata") or {"sourceClass": evidence_class},
                "results": [normalize_result(case_id, item, variant_index) for item in results if isinstance(item, dict)],
            }
        )

    require(cases, "round-results must contain at least one case")

    decision = round_results.get("decision") or {}
    return {
        "title": round_results.get("title") or "CE Prompt Improver Review",
        "kicker": round_results.get("kicker") or f"Manual Lab · {evidence_class}",
        "heroTitleHtml": round_results.get("heroTitleHtml") or round_results.get("title") or "CE Prompt Improver Review",
        "lede": round_results.get("lede") or "Prompt-lab comparison data generated from round-results.json.",
        "evidenceClass": evidence_class,
        "roundId": round_results.get("round_id") or round_results.get("roundId") or "round-01",
        "leftVariantId": round_results.get("left_variant_id") or round_results.get("leftVariantId") or variants[0]["id"],
        "defaultRightVariant": round_results.get("default_right_variant") or round_results.get("defaultRightVariant") or variants[1]["id"],
        "defaultCaseId": round_results.get("default_case_id") or round_results.get("defaultCaseId") or cases[0]["id"],
        "variants": variants,
        "cases": cases,
        "goalProgress": round_results.get("goalProgress") or {},
        "overallAnalysis": round_results.get("overallAnalysis") or {},
        "metricMatrix": round_results.get("metricMatrix") or [],
        "decisionMetrics": round_results.get("decisionMetrics") or {},
        "decisionScorecard": round_results.get("decisionScorecard")
        or {
            "verdict": decision.get("verdict") or "pending",
            "recommendedNextStep": decision.get("recommended_next_step") or "pending_hitl",
            "confidence": decision.get("confidence") or "low",
        },
        "assistant_recommendation": round_results.get("assistant_recommendation") or round_results.get("assistantRecommendation") or {},
        "interpretationNotes": round_results.get("interpretationNotes") or {},
        "iterationPath": round_results.get("iterationPath") or [],
        "traceIntegrity": round_results.get("traceIntegrity")
        or {
            "status": "not_trace_verified" if evidence_class in STATIC_EVIDENCE_CLASSES else "pending_verification",
            "sourceClasses": [evidence_class],
        },
        "hitlDecision": round_results.get("hitlDecision")
        or {
            "status": "pending",
            "options": ["promote_to_provider_test", "revise_candidate", "keep_baseline", "split", "inconclusive"],
        },
        "preflightChecks": {
            "jsonValid": "pass",
            "builder": "ce-prompt-improver/scripts/build_review_data.py",
            "productionFilesTouched": False,
        },
        "notProven": round_results.get("notProven")
        or {
            "items": (
                [
                    "This is a layout smoke, not an A/B test.",
                    "Provider fidelity, latency, token cost, and production readiness are not proven.",
                ]
                if evidence_class in STATIC_EVIDENCE_CLASSES
                else [
                    "Production wiring is not proven by this lab packet.",
                    "Provider fidelity is only proven for the recorded run artifacts, not for all future runs.",
                ]
            )
        },
        "sourceLinks": round_results.get("sourceLinks") or [],
        "roundNavigation": round_results.get("roundNavigation") or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    data = build(load_json(args.round_results))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
