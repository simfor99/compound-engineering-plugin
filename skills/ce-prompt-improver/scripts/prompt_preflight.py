#!/usr/bin/env python3
"""Deterministic prompt preflight helpers for OpenSpec prompt A/B rounds."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROVIDER_RULES = [
    ("perplexity_sonar", "perplexity", r"\b(perplexity|sonar|search_domain_filter|search_recency_filter|web_search)\b"),
    ("openai_gpt_5_4", "openai", r"\b(openai|gpt-5\.?4|responses\.create|reasoning\.?effort|verbosity)\b"),
    ("claude_opus_4_6", "anthropic", r"\b(anthropic|claude|messages\.create|adaptive thinking)\b"),
    ("gemini_3_5_flash", "google", r"\b(googlegenai|gemini|generate_content|thinking_level)\b"),
]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_text(path: Path) -> str:
    return path.expanduser().read_text(encoding="utf-8")


def _status_from_findings(findings: list[dict[str, Any]], default: str = "green") -> str:
    if any(item.get("severity") == "red" for item in findings):
        return "red"
    if findings:
        return "yellow"
    return default


def prompt_contract_view(prompt_text: str) -> tuple[str, dict[str, Any]]:
    """Return a prompt-contract view with bulky dynamic case payloads collapsed.

    Rendered stage prompts often contain the real input variables and scrape
    evidence. Those are important provider inputs, but they are not the static
    prompt contract we are trying to review for overfit or avoidable prompt
    bloat. Keep a small payload report so the rendered prompt still exposes
    runtime-size risk without turning every long customer page into a false
    prompt-contract blocker.
    """

    contract_text = prompt_text
    dynamic_sections: list[dict[str, Any]] = []

    patterns = [
        (
            "input_parameters",
            re.compile(r"\nInput parameters:\n.*?\n\nDefinitions:\n", flags=re.DOTALL),
            "\nInput parameters:\n[DYNAMIC INPUT PARAMETERS COLLAPSED]\n\nDefinitions:\n",
        ),
        (
            "scrape_evidence",
            re.compile(r"\nScrape evidence:\n.*?\n\nTask:\n", flags=re.DOTALL),
            "\nScrape evidence:\n[DYNAMIC SCRAPE EVIDENCE COLLAPSED]\n\nTask:\n",
        ),
    ]

    for section_id, pattern, replacement in patterns:
        match = pattern.search(contract_text)
        if not match:
            continue
        dynamic_sections.append(
            {
                "id": section_id,
                "char_count": len(match.group(0)),
                "sha256": _sha256_text(match.group(0)),
            }
        )
        contract_text = pattern.sub(replacement, contract_text, count=1)

    return contract_text, {
        "full_char_count": len(prompt_text),
        "contract_char_count": len(contract_text),
        "dynamic_sections": dynamic_sections,
    }


def classify_provider(prompt_text: str, provider_route: str | None = None, model: str | None = None) -> dict[str, Any]:
    haystack = "\n".join(part for part in [provider_route or "", model or "", prompt_text] if part)
    best_ruleset = "generic_llm"
    best_provider = "generic"
    best_score = 0.1
    evidence: list[str] = []
    for ruleset, provider, pattern in PROVIDER_RULES:
        hits = re.findall(pattern, haystack, flags=re.IGNORECASE)
        if hits:
            score = min(1.0, 0.35 + 0.15 * len(hits))
            if score > best_score:
                best_ruleset = ruleset
                best_provider = provider
                best_score = score
                evidence = [f"matched:{ruleset}", *(f"signal:{hit}" for hit in sorted(set(hits))[:5])]
    return {
        "provider": best_provider,
        "ruleset": best_ruleset,
        "confidence": round(best_score, 2),
        "evidence": evidence,
    }


def provider_fit(prompt_text: str, provider_route: str | None = None, model: str | None = None) -> dict[str, Any]:
    profile = classify_provider(prompt_text, provider_route, model)
    findings: list[dict[str, Any]] = []
    text = prompt_text.lower()

    if profile["ruleset"] == "generic_llm":
        findings.append(
            {
                "severity": "yellow",
                "id": "provider_profile_generic",
                "message": "Provider profile is generic; provider-specific risks must stay optional.",
            }
        )

    if profile["ruleset"] == "perplexity_sonar" and re.search(r"\b(example|few-shot|few shot|beispiel)\b", text):
        findings.append(
            {
                "severity": "yellow",
                "id": "perplexity_examples_may_dilute_retrieval",
                "message": "Perplexity/Sonar prompts should avoid example blocks unless evidence proves they help retrieval.",
            }
        )

    expects_json = bool(re.search(r"\b(json|schema|parsed output|parsebar|parseable)\b", text))
    has_json_hygiene = bool(re.search(r"\b(valid json|no markdown|keine markdown|parsebar|parseable|schema)\b", text))
    if expects_json and not has_json_hygiene:
        findings.append(
            {
                "severity": "yellow",
                "id": "json_contract_hygiene_unclear",
                "message": "The prompt appears schema-related but JSON hygiene is not explicit.",
            }
        )

    return {
        "status": _status_from_findings(findings),
        "profile": profile,
        "findings": findings,
    }


def simplicity(prompt_text: str, contract_text: str | None = None, payload_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    contract_text = contract_text or prompt_text
    lines = contract_text.splitlines()
    words = re.findall(r"\S+", contract_text)
    headings = [line for line in lines if line.lstrip().startswith("#")]
    rule_markers = re.findall(r"(^|\n)\s*(?:[-*]|\d+[.)])\s+", contract_text)
    longest_line = max((len(line) for line in lines), default=0)
    findings: list[dict[str, Any]] = []

    if len(contract_text) > 32000:
        findings.append({"severity": "red", "id": "prompt_too_large", "message": "Prompt exceeds 32k characters."})
    elif len(contract_text) > 16000:
        findings.append({"severity": "yellow", "id": "prompt_large", "message": "Prompt exceeds 16k characters; check for avoidable bulk."})
    elif payload_profile and int(payload_profile.get("full_char_count") or 0) > 32000:
        findings.append(
            {
                "severity": "yellow",
                "id": "dynamic_payload_large",
                "message": "Rendered prompt exceeds 32k characters because of dynamic input payload; monitor token budget separately from prompt-contract promotion.",
            }
        )
    if len(rule_markers) > 120:
        findings.append({"severity": "yellow", "id": "many_rules", "message": "Prompt has many rule markers; check for overlapping constraints."})
    if longest_line > 500:
        findings.append({"severity": "yellow", "id": "long_line", "message": "Prompt contract contains very long lines; review readability and truncation risk."})

    return {
        "status": _status_from_findings(findings),
        "metrics": {
            "char_count": len(contract_text),
            "full_char_count": len(prompt_text),
            "word_count": len(words),
            "line_count": len(lines),
            "heading_count": len(headings),
            "rule_marker_count": len(rule_markers),
            "longest_line_chars": longest_line,
        },
        "payloadProfile": payload_profile or {"full_char_count": len(prompt_text), "contract_char_count": len(contract_text), "dynamic_sections": []},
        "findings": findings,
    }


def hardcoding_scan(prompt_text: str) -> dict[str, Any]:
    urls = re.findall(r"\bhttps?://[^\s)>\"]+", prompt_text)
    domains = re.findall(r"\b[a-z0-9][a-z0-9-]{1,63}\.(?:com|de|net|org|io|ai|co|dev|app|cloud)\b", prompt_text, flags=re.IGNORECASE)
    emails = re.findall(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", prompt_text, flags=re.IGNORECASE)
    absolute_dates = re.findall(r"\b(?:20\d{2}|19\d{2})[-_/](?:0?[1-9]|1[0-2])[-_/](?:0?[1-9]|[12]\d|3[01])\b", prompt_text)
    example_markers = re.findall(r"\b(example|few-shot|few shot|beispiel|zum beispiel)\b", prompt_text, flags=re.IGNORECASE)
    findings: list[dict[str, Any]] = []

    concrete_count = len(urls) + len(domains) + len(emails) + len(absolute_dates)
    if concrete_count:
        findings.append(
            {
                "severity": "yellow",
                "id": "concrete_literals_present",
                "message": "Concrete URLs, domains, emails, or dates are present; verify they are target-contract invariants, not case fixes.",
                "counts": {
                    "urls": len(urls),
                    "domains": len(domains),
                    "emails": len(emails),
                    "absolute_dates": len(absolute_dates),
                },
            }
        )
    if example_markers:
        findings.append(
            {
                "severity": "yellow",
                "id": "examples_present",
                "message": "Examples are present; verify they show form only and do not contain current-case facts.",
                "count": len(example_markers),
            }
        )

    return {
        "status": _status_from_findings(findings),
        "findings": findings,
        "sampledSignals": {
            "urls": urls[:5],
            "domains": domains[:5],
            "emails": emails[:3],
            "absolute_dates": absolute_dates[:5],
        },
    }


def anti_overfit(prompt_text: str) -> dict[str, Any]:
    hardcoding = hardcoding_scan(prompt_text)
    findings = list(hardcoding["findings"])
    if re.search(r"\b(only for this|nur fuer diesen|nur für diesen|current case|aktueller fall)\b", prompt_text, flags=re.IGNORECASE):
        findings.append(
            {
                "severity": "red",
                "id": "case_specific_instruction",
                "message": "Prompt appears to contain case-specific optimization language.",
            }
        )
    return {
        "status": _status_from_findings(findings),
        "findings": findings,
    }


def eval_suite_hash(paths: list[Path]) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    combined = hashlib.sha256()
    for path in sorted({item.expanduser() for item in paths}, key=lambda item: str(item)):
        if not path.exists():
            components.append({"path": str(path), "status": "missing", "sha256": None})
            combined.update(f"{path}:missing".encode("utf-8"))
            continue
        text = _read_text(path).replace("\r\n", "\n")
        digest = _sha256_text(text)
        components.append({"path": str(path), "status": "present", "sha256": digest})
        combined.update(f"{path}:{digest}".encode("utf-8"))
    return {
        "evalSuiteHash": combined.hexdigest() if components else None,
        "components": components,
    }


def generalization(eval_files: list[Path] | None = None, has_train_test_split: bool = False, mutation_history_path: Path | None = None) -> dict[str, Any]:
    eval_files = eval_files or []
    suite = eval_suite_hash(eval_files)
    findings: list[dict[str, Any]] = []
    mutation_history_exists = bool(mutation_history_path and mutation_history_path.expanduser().exists())
    if not eval_files:
        status = "neutral"
        findings.append(
            {
                "severity": "info",
                "id": "eval_suite_not_supplied",
                "message": "No eval suite files were supplied; train/test evidence is not available for this preflight.",
            }
        )
    elif not has_train_test_split:
        status = "yellow"
        findings.append(
            {
                "severity": "yellow",
                "id": "train_test_split_not_marked",
                "message": "Eval files exist, but train/test separation was not marked.",
            }
        )
    else:
        status = "green"

    return {
        "status": status,
        "evalSuiteHash": suite["evalSuiteHash"],
        "components": suite["components"],
        "trainTestSplit": "present" if has_train_test_split else "not_available",
        "mutationHistory": "present" if mutation_history_exists else "not_available",
        "findings": findings,
    }


def build_preflight_check(
    prompt_text: str,
    *,
    case_id: str = "",
    variant_id: str = "",
    provider_route: str | None = None,
    model: str | None = None,
    eval_files: list[Path] | None = None,
    has_train_test_split: bool = False,
    mutation_history_path: Path | None = None,
) -> dict[str, Any]:
    contract_text, payload_profile = prompt_contract_view(prompt_text)
    provider = provider_fit(prompt_text, provider_route, model)
    simple = simplicity(prompt_text, contract_text, payload_profile)
    hardcoding = hardcoding_scan(contract_text)
    overfit = anti_overfit(contract_text)
    general = generalization(eval_files, has_train_test_split, mutation_history_path)
    statuses = [provider["status"], simple["status"], hardcoding["status"], overfit["status"], general["status"]]
    overall = "red" if "red" in statuses else "yellow" if "yellow" in statuses else "green"
    return {
        "provenance": "deterministic_prompt_preflight",
        "caseId": case_id,
        "variantId": variant_id,
        "status": overall,
        "providerFit": provider,
        "simplicity": simple,
        "hardcodingScan": hardcoding,
        "antiOverfit": overfit,
        "generalization": general,
    }


def build_preflight_for_result(result: dict[str, Any], case_id: str, variant_id: str) -> dict[str, Any]:
    prompt = result.get("prompt") if isinstance(result.get("prompt"), dict) else {}
    prompt_text = "\n\n".join(
        str(prompt.get(key) or "")
        for key in ("system", "user")
        if isinstance(prompt, dict)
    )
    return build_preflight_check(
        prompt_text,
        case_id=case_id,
        variant_id=variant_id,
        provider_route=str(result.get("providerRoute") or ""),
        model=str(result.get("model") or ""),
    )


def summarize_preflight(checks: list[dict[str, Any]]) -> dict[str, Any]:
    by_variant: dict[str, list[str]] = {}
    for check in checks:
        variant_id = str(check.get("variantId") or "unknown")
        by_variant.setdefault(variant_id, []).append(str(check.get("status") or "neutral"))
    variants = {}
    for variant_id, statuses in by_variant.items():
        status = "red" if "red" in statuses else "yellow" if "yellow" in statuses else "green"
        variants[variant_id] = {"status": status, "checks": len(statuses)}
    overall_statuses = [item["status"] for item in variants.values()]
    overall = "red" if "red" in overall_statuses else "yellow" if "yellow" in overall_statuses else "green" if overall_statuses else "neutral"
    return {
        "provenance": "deterministic_prompt_preflight",
        "status": overall,
        "variants": variants,
        "items": checks,
    }
