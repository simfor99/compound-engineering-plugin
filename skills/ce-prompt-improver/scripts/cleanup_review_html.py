#!/usr/bin/env python3
"""Delete rendered static review HTML after the human decision no longer needs it."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DECISIONS = {
    "promote_candidate",
    "revise_candidate",
    "keep_baseline",
    "split_candidate",
    "inconclusive",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def default_receipt(html_path: Path) -> Path:
    round_dir = html_path.parent.parent if html_path.parent.name == "html" else html_path.parent
    return round_dir / "artifacts" / "review-html-cleanup.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path, help="Path to rendered html/index.html")
    parser.add_argument("--decision", required=True, choices=sorted(DECISIONS), help="HITL decision that made the HTML disposable")
    parser.add_argument("--receipt", type=Path, help="Cleanup receipt path")
    parser.add_argument("--keep-as-export-archive", action="store_true")
    args = parser.parse_args()

    html = args.html.expanduser().resolve()
    if html.name != "index.html" or html.parent.name != "html":
        raise SystemExit("cleanup target must be a round html/index.html file")
    data_path = html.parent / "assets" / "data.json"
    if not data_path.exists():
        raise SystemExit("cleanup target must have sibling html/assets/data.json evidence")
    receipt = (args.receipt.expanduser().resolve() if args.receipt else default_receipt(html))

    status = "already_absent"
    if args.keep_as_export_archive:
        status = "kept_as_export_archive" if html.exists() else "archive_requested_but_absent"
    elif html.exists():
        html.unlink()
        status = "deleted_after_decision"

    payload = {
        "status": status,
        "decision": args.decision,
        "htmlPath": str(html),
        "cleanupAt": utc_now(),
        "scope": "rendered_static_html_only",
        "retainedEvidence": [
            "html/assets/data.json",
            "artifacts/",
            "round-brief.md",
            "promotion packet or inconclusive packet",
        ],
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
