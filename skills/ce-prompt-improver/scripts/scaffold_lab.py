#!/usr/bin/env python3
"""Scaffold a CE Prompt Improver lab without inventing a new daily workspace."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()
    return value or "ce-prompt-improver-lab"


def source_day_dir(source: Path | None) -> Path | None:
    if source is None:
        return None
    parts = source.resolve().parts
    for idx, part in enumerate(parts):
        if part == "docs" and idx + 2 < len(parts) and parts[idx + 1] == "todo":
            return Path(*parts[: idx + 3])
    return None


def next_prefix(day_dir: Path) -> int:
    max_prefix = 0
    if day_dir.exists():
        for path in day_dir.rglob("[0-9][0-9][0-9]_*"):
            match = re.match(r"^(\d{3})_", path.name)
            if match:
                max_prefix = max(max_prefix, int(match.group(1)))
    return max_prefix + 1


def write_if_missing(path: Path, text: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def campaign_path(args: argparse.Namespace) -> tuple[Path, str]:
    timestamp = args.timestamp or datetime.now().strftime("%Y_%m_%d__%H-%M")
    safe_slug = slugify(args.slug)

    if args.campaign:
        return args.campaign, "explicit_campaign"

    if args.day_dir:
        day_dir = args.day_dir
        prefix = next_prefix(day_dir)
        return (
            day_dir / "07_experiments" / f"{prefix:03d}_ce-prompt-improver-{safe_slug}__{timestamp}",
            "explicit_day_dir",
        )

    inferred_day = source_day_dir(args.source)
    if inferred_day:
        prefix = next_prefix(inferred_day)
        return (
            inferred_day / "07_experiments" / f"{prefix:03d}_ce-prompt-improver-{safe_slug}__{timestamp}",
            "source_day_dir",
        )

    return (
        args.workspace_root / safe_slug / timestamp,
        "fallback_non_render_workspace",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--goal", default="TBD")
    parser.add_argument("--target", default="TBD")
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--day-dir", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=Path(".context/compound-engineering/ce-prompt-improver"))
    parser.add_argument("--timestamp")
    args = parser.parse_args()

    campaign, workspace_reason = campaign_path(args)
    campaign.mkdir(parents=True, exist_ok=True)

    round_dir = campaign / "03_rounds" / "round-01-manual"
    for directory in [
        campaign / "01_intake",
        campaign / "02_cases",
        round_dir / "baseline",
        round_dir / "variant",
        round_dir / "comparisons",
        round_dir / "html" / "assets",
        round_dir / "artifacts",
        campaign / "04_decisions",
        campaign / "05_promotion-packets",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    state = {
        "schema_version": 1,
        "skill": "compound-engineering:ce-prompt-improver",
        "mode": "manual",
        "status": "scaffolded",
        "workspace_reason": workspace_reason,
        "campaign": str(campaign),
        "source": str(args.source) if args.source else None,
        "goal": args.goal,
        "target": args.target,
        "active_round": "round-01-manual",
        "hitl_decision": "pending",
        "guardrail": "No current-date docs/todo workspace is created unless --day-dir or --campaign says so.",
    }
    write_if_missing(campaign / "campaign-state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    write_if_missing(
        campaign / "README.md",
        f"""# CE Prompt Improver Lab

Status: `scaffolded`

Goal: {args.goal}

Target: `{args.target}`

Workspace reason: `{workspace_reason}`

This is a prompt lab. It does not wire production prompts, schemas, runtime parsers, or dashboard consumers.
""",
    )
    write_if_missing(
        campaign / "01_intake" / "lab-brief.md",
        """# Lab-Brief

## Ziel

TBD

## Baseline

Source-Klasse: `current_runtime_evidence | target_contract | proposed_shape | example_only`

## Candidate-Hebel

TBD

## Must-survive

- TBD

## Must-reject

- TBD

## Downstream-Consumer

TBD
""",
    )
    write_if_missing(
        campaign / "02_cases" / "cases.json",
        json.dumps(
            {
                "schema_version": 1,
                "cases": [
                    {
                        "id": "case-01",
                        "title": "TBD",
                        "source_class": "layout_smoke_not_ab_test",
                        "intent": "TBD",
                        "expected_behavior": "TBD",
                        "watch_for": "TBD",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    write_if_missing(
        round_dir / "round-results.json",
        json.dumps(
            {
                "schema_version": 1,
                "round_id": "round-01-manual",
                "title": "Round 01",
                "evidence_class": "layout_smoke_not_ab_test",
                "left_variant_id": "baseline",
                "default_right_variant": "candidate",
                "variants": [
                    {"id": "baseline", "label": "Baseline", "shortLabel": "A"},
                    {"id": "candidate", "label": "Candidate", "shortLabel": "B"},
                ],
                "cases": [],
                "decision": {
                    "verdict": "pending",
                    "recommended_next_step": "pending_hitl",
                    "confidence": "low",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    write_if_missing(campaign / "04_decisions" / "hitl-decision.md", "# HITL-Entscheidung\n\nStatus: `pending`\n")
    write_if_missing(campaign / "05_promotion-packets" / "README.md", "# Promotion-Packets\n\nStatus: `not_started`\n")

    print(campaign)
    if workspace_reason == "fallback_non_render_workspace":
        print(
            "warning: fallback workspace is not docs/todo; React review routes may not load html/assets/data.json",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
