#!/usr/bin/env python3
"""Evaluate one prompt/provider response for Pre-Spec prompt optimization."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


CITATION_RE = re.compile(r"\[(?:\d+|web:\d+|page:[^\]]+)\]")
EXAMPLE_RE = re.compile(r"\b(acme-|example\.|Fleet Maintenance Audit)\b", re.I)


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
        raise
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
    raise json.JSONDecodeError("No complete JSON object found", stripped, start)


def iter_strings(value: object) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        for item in value:
            out.extend(iter_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            out.extend(iter_strings(item))
    return out


def collect_source_refs(value: object) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    if isinstance(value, dict):
        maybe = value.get("source_refs")
        if isinstance(maybe, list):
            refs.extend(item for item in maybe if isinstance(item, dict))
        for item in value.values():
            refs.extend(collect_source_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.extend(collect_source_refs(item))
    return refs


def host_matches(url: str, expected_host: str | None) -> bool:
    if not expected_host:
        return True
    host = urlparse(url).netloc.lower()
    expected = expected_host.lower().removeprefix("www.")
    return host == expected or host.endswith("." + expected) or host.removeprefix("www.") == expected


def evaluate(text: str, expected_object: str | None, expected_host: str | None) -> tuple[object | None, dict[str, object]]:
    parsed: object | None = None
    parse_error: str | None = None
    try:
        parsed = extract_json(text)
    except Exception as exc:  # noqa: BLE001
        parse_error = str(exc)

    strings = iter_strings(parsed) if parsed is not None else []
    source_refs = collect_source_refs(parsed) if parsed is not None else []
    source_urls = [str(ref.get("url", "")) for ref in source_refs if ref.get("url")]
    citation_strings = [value for value in strings if CITATION_RE.search(value)]
    example_leaks = [value for value in strings if EXAMPLE_RE.search(value)]

    schema_ok = False
    if isinstance(parsed, dict):
        schema_ok = bool(expected_object is None or expected_object in parsed)

    metrics: dict[str, object] = {
        "schema_ok": schema_ok,
        "parse_error": parse_error,
        "related_count": 0,
        "source_ref_count": len(source_refs),
        "first_party_source_ref_count": sum(1 for url in source_urls if host_matches(url, expected_host)),
        "citation_marker_count": len(citation_strings),
        "example_leak_count": len(example_leaks),
        "strings_with_citation_markers": citation_strings,
        "example_leak_strings": example_leaks,
        "source_ref_urls": source_urls,
    }

    if isinstance(parsed, dict):
        pwc = parsed.get("product_world_context")
        if isinstance(pwc, dict):
            related = pwc.get("related_offerings")
            if isinstance(related, list):
                metrics["related_count"] = len(related)
            focus = pwc.get("focus_offering")
            if isinstance(focus, dict):
                metrics["focus_anchor_warnings_is_array"] = isinstance(
                    focus.get("focus_anchor_warnings"), list
                )

    return parsed, metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--response-text", type=Path, required=True)
    parser.add_argument("--expected-object")
    parser.add_argument("--expected-host")
    parser.add_argument("--parsed-out", type=Path)
    parser.add_argument("--metrics-out", type=Path)
    args = parser.parse_args()

    text = args.response_text.read_text(encoding="utf-8")
    parsed, metrics = evaluate(text, args.expected_object, args.expected_host)

    if args.parsed_out:
        args.parsed_out.parent.mkdir(parents=True, exist_ok=True)
        args.parsed_out.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.metrics_out:
        args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0 if metrics["parse_error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
