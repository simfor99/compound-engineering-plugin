#!/usr/bin/env python3
"""Merge reviewed display/enrichment fields into PromptReview data.

Use this after the OpenSpec-compatible builder has created a trace-backed
`html/assets/data.json`. The merge lets a CE lab reuse or apply richer review
copy, round navigation, test intent, scorecards, and HITL decision support
without pretending those fields came from a provider call.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DISPLAY_KEYS = [
    "title",
    "kicker",
    "heroTitleHtml",
    "lede",
    "roundId",
    "sourcePromptContract",
    "sourceFoundation",
    "testsetSource",
    "scorecards",
    "testIntent",
    "goalProgress",
    "overallAnalysis",
    "decisionMetrics",
    "decisionScorecard",
    "assistant_recommendation",
    "assistantRecommendation",
    "metricMatrix",
    "interpretationNotes",
    "iterationPath",
    "traceIntegrity",
    "hitlDecision",
    "preflightChecks",
    "recommendation",
    "notProven",
    "sourceLinks",
    "roundNavigation",
    "copy",
    "outputViewMode",
    "outputTreeDefaultExpanded",
]

CORE_KEYS = ["variants", "cases", "leftVariantId", "defaultRightVariant", "defaultCaseId", "evidenceClass"]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True, help="Builder-produced PromptReview data.")
    parser.add_argument("--overrides", type=Path, required=True, help="Reference/enrichment PromptReview data.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--copy-core", action="store_true", help="Also copy variants/cases/default ids from overrides.")
    parser.add_argument("--key", action="append", default=[], help="Additional top-level key to copy.")
    args = parser.parse_args()

    data = load_json(args.data)
    overrides = load_json(args.overrides)
    keys = list(DISPLAY_KEYS) + list(args.key)
    if args.copy_core:
        keys.extend(CORE_KEYS)

    for key in keys:
        if key in overrides:
            data[key] = overrides[key]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
