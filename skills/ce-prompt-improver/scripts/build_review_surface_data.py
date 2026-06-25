#!/usr/bin/env python3
"""Build Prompt A/B Review Surface data.json from Pre-Spec round evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from prompt_preflight import build_preflight_for_result, summarize_preflight


TRACE_KEYS = ("request", "renderedPrompt", "rawResponse", "responseText", "parsedOutput", "metrics")

MATRIX_ROWS = [
    {
        "id": "round_goal_fit",
        "group": "primary",
        "label": "Rundenziel",
        "meaning": "Welche Variante erfüllt das konkrete Rundenziel fachlich besser, falls überhaupt eine Variante promotefähig ist?",
        "provenance": "assistant_review_or_metric_proxy",
    },
    {
        "id": "thesis_aligned_output_quality",
        "group": "primary",
        "label": "These",
        "meaning": "Ist der Output inhaltlich wirklich besser und nicht nur länger oder schöner?",
        "provenance": "assistant_review_or_not_available",
    },
    {
        "id": "downstream_usefulness",
        "group": "primary",
        "label": "Downstream",
        "meaning": "Kann die nächste Stufe ohne manuelle Reparatur mit dem Output arbeiten?",
        "provenance": "assistant_review_or_metric_proxy",
    },
    {
        "id": "parsed_ok",
        "group": "guardrail",
        "label": "Parse",
        "meaning": "Ist der Provider-Output vollständig parsebar?",
        "provenance": "provider_runtime_metric",
    },
    {
        "id": "schema_ok",
        "group": "guardrail",
        "label": "Schema",
        "meaning": "Hält der Output den erwarteten JSON- oder Output-Vertrag?",
        "provenance": "provider_runtime_metric",
    },
    {
        "id": "must_survive_preserved",
        "group": "guardrail",
        "label": "Survive",
        "meaning": "Sind die Must-Survive-Fakten der Runde sichtbar erhalten?",
        "provenance": "metric_proxy_or_not_available",
    },
    {
        "id": "must_reject_removed",
        "group": "guardrail",
        "label": "Reject",
        "meaning": "Wurden explizit unerwünschte Bestandteile entfernt?",
        "provenance": "provider_runtime_metric",
    },
    {
        "id": "trace_complete",
        "group": "guardrail",
        "label": "Trace",
        "meaning": "Sind die sechs erwarteten Lab-Artefakte sichtbar?",
        "provenance": "lab_runner_artifact_set",
    },
    {
        "id": "contract_violation_count",
        "group": "guardrail",
        "label": "Brüche",
        "meaning": "Wie viele klare Vertragsbrüche enthält der Output?",
        "provenance": "provider_runtime_metric",
    },
    {
        "id": "input_tokens",
        "group": "monitoring",
        "label": "Input-Tokens",
        "meaning": "Promptgröße und Input-Kosten. Niedriger ist nur bei gleicher Qualität besser.",
        "provenance": "provider_runtime_metadata",
    },
    {
        "id": "output_tokens",
        "group": "monitoring",
        "label": "Output-Tokens",
        "meaning": "Ausgabelänge und Kosten. Niedriger ist nur bei gleicher Qualität besser.",
        "provenance": "provider_runtime_metadata",
    },
    {
        "id": "duration_ms",
        "group": "monitoring",
        "label": "Laufzeit",
        "meaning": "Provider-Laufzeit. Monitoring erklärt Nebenwirkungen, entscheidet aber nicht die Promotion.",
        "provenance": "provider_runtime_metadata",
    },
    {
        "id": "cost_estimate",
        "group": "monitoring",
        "label": "Kosten",
        "meaning": "Geschätzte Provider-Kosten, sofern verfügbar.",
        "provenance": "provider_runtime_metadata",
    },
    {
        "id": "semantic_coverage",
        "group": "assistant_review",
        "label": "Semantik",
        "meaning": "Deckt der Output die richtige Bedeutung ab?",
        "provenance": "assistant_review",
    },
    {
        "id": "source_grounding",
        "group": "assistant_review",
        "label": "Grounding",
        "meaning": "Ist der Output sauber aus Quellen oder Evidence abgeleitet?",
        "provenance": "assistant_review",
    },
    {
        "id": "contract_discipline",
        "group": "assistant_review",
        "label": "Vertrag",
        "meaning": "Hält der Output Format, Scope und Aufgabe ein?",
        "provenance": "assistant_review",
    },
    {
        "id": "completion_fit",
        "group": "assistant_review",
        "label": "Vollständigkeit",
        "meaning": "Ist der Output vollständig genug für das Rundenziel?",
        "provenance": "assistant_review",
    },
    {
        "id": "breadth_vs_budget",
        "group": "assistant_review",
        "label": "Breite/Budget",
        "meaning": "Liefert der Output genug Breite ohne unnötig auszuufern?",
        "provenance": "assistant_review",
    },
]

DECISION_METRIC_AXIS_ORDER = (
    "round_goal_fit",
    "thesis_aligned_output_quality",
    "downstream_usefulness",
    "contract_violation_count",
    "parsed_ok",
    "schema_ok",
    "must_survive_preserved",
    "must_reject_removed",
    "trace_complete",
)

DECISION_METRIC_AXIS_META = {
    "round_goal_fit": {
        "label": "Rundenziel-Fit",
        "shortLabel": "Ziel",
        "listLabel": "Rundenziel",
        "description": "Passt die Variante zum Zweck dieser Runde und liefert sie eine verwertbare Entscheidung?",
    },
    "thesis_aligned_output_quality": {
        "label": "Thesennahe Outputqualität",
        "shortLabel": "These",
        "description": "Stützt der Output die getestete These mit Inhalt, Evidence und nachvollziehbarer Begründung?",
    },
    "downstream_usefulness": {
        "label": "Downstream-Nützlichkeit",
        "shortLabel": "Downstream",
        "description": "Kann die nächste Stufe mit dem Output weiterarbeiten, ohne ihn manuell zu reparieren?",
    },
    "contract_violation_count": {
        "label": "Contract-Verletzungen",
        "shortLabel": "Contract",
        "chartLabel": "Brüche",
        "listLabel": "Brüche",
        "description": "Hoher Score bedeutet: wenige oder keine sichtbaren Vertragsverletzungen.",
    },
    "parsed_ok": {
        "label": "Parsebarkeit",
        "shortLabel": "Parse",
        "description": "Der Provider-Output ist als JSON oder vereinbarter Output lesbar.",
    },
    "schema_ok": {
        "label": "Schema-Fit",
        "shortLabel": "Schema",
        "description": "Der Output erfüllt den erwarteten JSON- oder Output-Vertrag.",
    },
    "must_survive_preserved": {
        "label": "Must-survive erhalten",
        "shortLabel": "Survive",
        "description": "Die Kernsignale der Runde bleiben im Output sichtbar erhalten.",
    },
    "must_reject_removed": {
        "label": "Must-reject entfernt",
        "shortLabel": "Reject",
        "description": "Unerwünschte Beispielreste, Citation-Altlasten oder Contract-Leaks fehlen.",
    },
    "trace_complete": {
        "label": "Trace vollständig",
        "shortLabel": "Trace",
        "description": "Die Review-Fläche ist auf Request, Prompt, Response, Parsed Output und Metrics zurückführbar.",
    },
}


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


EXPECTED_ARTIFACT_LOAD_ERRORS = (
    FileNotFoundError,
    PermissionError,
    UnicodeDecodeError,
    json.JSONDecodeError,
)


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_rendered_prompt(text: str) -> dict[str, str]:
    system, separator, user = text.partition("\n\n")
    if not separator:
        return {"system": "", "user": text}
    return {"system": system.rstrip(), "user": user.rstrip()}


def prompt_from_artifacts(item: dict[str, object], summary_path: Path | None) -> dict[str, str]:
    prompt = item.get("prompt")
    if isinstance(prompt, dict):
        return {
            "system": str(prompt.get("system") or ""),
            "user": str(prompt.get("user") or ""),
        }

    system_prompt = item.get("system_prompt")
    user_prompt = item.get("user_prompt")
    if isinstance(system_prompt, str) or isinstance(user_prompt, str):
        return {
            "system": str(system_prompt or ""),
            "user": str(user_prompt or ""),
        }

    artifact_base = item.get("artifact_base") or item.get("artifactBase")
    if not isinstance(artifact_base, str) or not artifact_base:
        return {"system": "", "user": ""}

    base = Path(artifact_base)
    candidates = [base.with_name(base.name + "__02_rendered-prompt.txt")]
    if summary_path is not None and not base.is_absolute():
        candidates.append((summary_path.parent / base).with_name(base.name + "__02_rendered-prompt.txt"))
        candidates.append((summary_path.parent.parent / base).with_name(base.name + "__02_rendered-prompt.txt"))

    for candidate in candidates:
        if candidate.exists():
            return split_rendered_prompt(candidate.read_text(encoding="utf-8"))

    return {"system": "", "user": ""}


def artifact_paths(item: dict[str, object], summary_path: Path | None) -> dict[str, Path]:
    artifact_base = item.get("artifact_base") or item.get("artifactBase")
    if not isinstance(artifact_base, str) or not artifact_base:
        return {}
    base = Path(artifact_base)
    names = {
        "request": "__01_request.json",
        "renderedPrompt": "__02_rendered-prompt.txt",
        "rawResponse": "__03_raw-response.json",
        "responseText": "__04_response-text.txt",
        "parsedOutput": "__05_parsed-output.json",
        "metrics": "__06_metrics.json",
    }
    if summary_path is not None and not base.is_absolute():
        candidates = [
            base,
            Path.cwd() / base,
            summary_path.parent / base,
            summary_path.parent.parent / base,
        ]
        for candidate in candidates:
            raw_candidate = candidate.with_name(candidate.name + names["rawResponse"])
            if raw_candidate.exists():
                base = candidate
                break
    return {key: base.with_name(base.name + suffix) for key, suffix in names.items()}


def provider_metadata(item: dict[str, object], summary_path: Path | None) -> dict[str, object]:
    model = item.get("model")
    token_usage = item.get("token_usage") or item.get("tokenUsage")
    called_at = item.get("provider_called_at") or item.get("providerCalledAt") or item.get("called_at") or item.get("calledAt")

    paths = artifact_paths(item, summary_path)
    raw_path = paths.get("rawResponse")
    if raw_path and raw_path.exists():
        try:
            raw = load_json(raw_path)
            if isinstance(raw, dict):
                model = model or raw.get("model")
                metadata = raw.get("metadata")
                if called_at is None and isinstance(metadata, dict):
                    called_at = metadata.get("calledAt") or metadata.get("called_at")
                usage = raw.get("usage")
                if token_usage is None and isinstance(usage, dict):
                    token_usage = usage
        except EXPECTED_ARTIFACT_LOAD_ERRORS as exc:
            print(f"Warning: could not load provider metadata from {raw_path}: {exc}", file=sys.stderr)

    request = item.get("request_without_secret") or item.get("requestWithoutSecret")
    if not isinstance(request, dict):
        paths = artifact_paths(item, summary_path)
        request_path = paths.get("request")
        if request_path and request_path.exists():
            try:
                loaded = load_json(request_path)
                request = loaded if isinstance(loaded, dict) else {}
            except EXPECTED_ARTIFACT_LOAD_ERRORS as exc:
                print(f"Warning: could not load request metadata from {request_path}: {exc}", file=sys.stderr)
                request = {}

    return {
        "model": model,
        "tokenUsage": token_usage if isinstance(token_usage, dict) else None,
        "maxOutputTokens": request.get("max_output_tokens") if isinstance(request, dict) else item.get("max_output_tokens"),
        "providerCalledAt": called_at if isinstance(called_at, str) else None,
    }


def response_text_from_artifacts(item: dict[str, object], summary_path: Path | None) -> str:
    paths = artifact_paths(item, summary_path)
    response_path = paths.get("responseText")
    if response_path and response_path.exists():
        return response_path.read_text(encoding="utf-8")
    return str(item.get("response_text") or item.get("responseText") or "")


def artifact_trace(item: dict[str, object], summary_path: Path | None) -> dict[str, object]:
    paths = artifact_paths(item, summary_path)
    refs = {}
    hashes = {}
    for key, path in paths.items():
        refs[key] = str(path)
        hashes[key] = sha256_file(path)
    return {
        "artifactBase": item.get("artifact_base") or item.get("artifactBase"),
        "artifactRefs": refs,
        "artifactSha256": hashes,
        "provenance": "lab_runner_artifact_set",
    }


def build_trace_integrity(data: dict[str, object]) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
        if not isinstance(case, dict):
            continue
        for result in case.get("results", []) if isinstance(case.get("results"), list) else []:
            if not isinstance(result, dict):
                continue
            trace = result.get("trace") if isinstance(result.get("trace"), dict) else {}
            hashes = trace.get("artifactSha256") if isinstance(trace, dict) else {}
            refs = trace.get("artifactRefs") if isinstance(trace, dict) else {}
            present = [key for key in TRACE_KEYS if isinstance(hashes, dict) and bool(hashes.get(key))]
            missing = [key for key in TRACE_KEYS if key not in present]
            items.append(
                {
                    "caseId": result.get("caseId") or case.get("id"),
                    "variantId": result.get("variantId"),
                    "status": "pass" if not missing else "fail",
                    "present": present,
                    "missing": missing,
                    "artifactRefs": refs if isinstance(refs, dict) else {},
                }
            )

    if not items:
        return {
            "provenance": "lab_runner_artifact_set",
            "status": "not_available",
            "expectedArtifacts": list(TRACE_KEYS),
            "summary": "Keine Lab-Runner-Resultate gefunden.",
            "items": [],
        }

    failing = [item for item in items if item.get("status") != "pass"]
    return {
        "provenance": "lab_runner_artifact_set",
        "status": "fail" if failing else "pass",
        "expectedArtifacts": list(TRACE_KEYS),
        "summary": (
            f"{len(items) - len(failing)}/{len(items)} Resultate haben alle sechs Lab-Artefakte."
            if failing
            else f"{len(items)}/{len(items)} Resultate haben alle sechs Lab-Artefakte."
        ),
        "items": items,
    }


def build_hitl_decision(summary: dict[str, object] | None = None) -> dict[str, object]:
    summary = summary or {}
    raw_decision = summary.get("hitl_decision") or summary.get("hitlDecision")
    allowed = [
        "promote_candidate",
        "iterate_same_lever",
        "change_lever",
        "split_decision",
        "reject",
        "inconclusive",
    ]
    if isinstance(raw_decision, dict):
        decision = {**raw_decision}
        decision.setdefault("status", "decided")
        decision.setdefault("hitl_required", True)
        decision.setdefault("allowed_decisions", allowed)
        return decision
    if isinstance(raw_decision, str) and raw_decision:
        return {
            "provenance": "markdown_decision_ledger_or_summary",
            "status": "decided",
            "decision": raw_decision,
            "hitl_required": True,
            "allowed_decisions": allowed,
        }
    return {
        "provenance": "pending_hitl_decision",
        "status": "pending",
        "decision": None,
        "hitl_required": True,
        "allowed_decisions": allowed,
        "summary": "Promotion bleibt offen, bis Simon/HITL eine Round-Entscheidung im Ledger festhält.",
    }


def number_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def average(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return sum(usable) / len(usable)


def status_from_score(score: float | None) -> str:
    if score is None:
        return "neutral"
    if score >= 4.2:
        return "green"
    if score >= 3:
        return "yellow"
    return "red"


def score_bool(ok: object) -> float | None:
    if isinstance(ok, bool):
        return 5.0 if ok else 0.0
    return None


def trace_count(result: dict[str, object]) -> int:
    trace = result.get("trace")
    if not isinstance(trace, dict):
        return 0
    refs = trace.get("artifactRefs")
    hashes = trace.get("artifactSha256")
    count = 0
    for key in TRACE_KEYS:
        ref_ok = isinstance(refs, dict) and bool(refs.get(key))
        hash_ok = isinstance(hashes, dict) and bool(hashes.get(key))
        if ref_ok or hash_ok:
            count += 1
    return count


def reject_signal_count(result: dict[str, object]) -> int:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    strings_with_citations = metrics.get("strings_with_citation_markers")
    example_leaks = metrics.get("example_leak_strings")
    return int(metrics.get("example_leak_count") or 0) + int(metrics.get("citation_marker_count") or 0) + (
        len(strings_with_citations) if isinstance(strings_with_citations, list) else 0
    ) + (len(example_leaks) if isinstance(example_leaks, list) else 0) + (1 if metrics.get("provider_error") else 0)


def contract_violation_count(result: dict[str, object]) -> int:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    count = 0
    if result.get("parsedOk") is False:
        count += 1
    if metrics.get("schema_ok") is False:
        count += 1
    if metrics.get("provider_error"):
        count += 1
    count += reject_signal_count(result)
    return count


def assistant_score(data: dict[str, object], case_id: str, variant_id: str, axis_id: str) -> float | None:
    evaluation = data.get("assistantEvaluation")
    if not isinstance(evaluation, dict):
        return None
    cases = evaluation.get("cases")
    if not isinstance(cases, dict):
        return None
    case_eval = cases.get(case_id)
    if not isinstance(case_eval, dict):
        return None
    variants = case_eval.get("variants")
    if not isinstance(variants, dict):
        return None
    variant_eval = variants.get(variant_id)
    if not isinstance(variant_eval, dict):
        return None
    scores: list[float | None] = []
    for group in ("standard", "context"):
        group_scores = variant_eval.get(group)
        if isinstance(group_scores, dict):
            scores.append(number_value(group_scores.get(axis_id)))
    return average(scores)


def result_metric_number(result: dict[str, object], key: str) -> float | None:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return number_value(metrics.get(key))


def has_metric(result: dict[str, object], key: str) -> bool:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return key in metrics


def dashboard_context_score(result: dict[str, object]) -> float | None:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    raw_score = number_value(metrics.get("dashboard_context_score"))
    if raw_score is None:
        return None
    return max(0.0, min(5.0, raw_score / 8.0 * 5.0))


def dashboard_context_downstream_score(result: dict[str, object]) -> float | None:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    if "dashboard_context_present" not in metrics:
        return None
    if metrics.get("dashboard_context_present") is True and metrics.get("dashboard_context_pass") is True:
        return 5.0
    if metrics.get("dashboard_context_present") is True:
        return 2.5
    return 1.0


def token_number(result: dict[str, object], key: str) -> float | None:
    token_usage = result.get("tokenUsage")
    if not isinstance(token_usage, dict):
        return None
    return number_value(token_usage.get(key))


def cost_number(result: dict[str, object]) -> float | None:
    token_usage = result.get("tokenUsage")
    if not isinstance(token_usage, dict):
        return None
    cost = token_usage.get("cost")
    if not isinstance(cost, dict):
        return None
    return number_value(cost.get("total_cost"))


def score_for_metric(data: dict[str, object], case_id: str, variant_id: str, result: dict[str, object], metric_id: str) -> float | None:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    if metric_id == "round_goal_fit":
        assistant = average(
            [
                assistant_score(data, case_id, variant_id, "product_world_items"),
                assistant_score(data, case_id, variant_id, "focus_anchor_control"),
                assistant_score(data, case_id, variant_id, "breadth_vs_budget"),
                assistant_score(data, case_id, variant_id, "completion_fit"),
            ]
        )
        if assistant is not None:
            return assistant
        context_score = dashboard_context_score(result)
        if context_score is not None:
            return average(
                [
                    context_score,
                    score_bool(metrics.get("baseline_preservation_pass")),
                    score_bool(metrics.get("schema_ok")),
                ]
            )
        return average(
            [
                score_bool(result.get("parsedOk")),
                score_bool(metrics.get("schema_ok")),
                score_for_metric(data, case_id, variant_id, result, "must_survive_preserved"),
                score_for_metric(data, case_id, variant_id, result, "must_reject_removed"),
            ]
        )
    if metric_id == "thesis_aligned_output_quality":
        assistant = average(
            [
                assistant_score(data, case_id, variant_id, "semantic_coverage"),
                assistant_score(data, case_id, variant_id, "source_grounding"),
                assistant_score(data, case_id, variant_id, "contract_discipline"),
                assistant_score(data, case_id, variant_id, "completion_fit"),
                assistant_score(data, case_id, variant_id, "downstream_usefulness"),
            ]
        )
        if assistant is not None:
            return assistant
        context_score = dashboard_context_score(result)
        if context_score is not None:
            return context_score
        refs = result_metric_number(result, "source_ref_count")
        content = result_metric_number(result, "content_character_count") or result_metric_number(result, "markdown_character_count")
        grounding_proxy = 5.0 if refs and content else 4.2 if refs else None
        return average(
            [
                score_bool(metrics.get("schema_ok")),
                score_for_metric(data, case_id, variant_id, result, "must_survive_preserved"),
                score_for_metric(data, case_id, variant_id, result, "downstream_usefulness"),
                grounding_proxy,
            ]
        )
    if metric_id == "downstream_usefulness":
        assistant = assistant_score(data, case_id, variant_id, "downstream_usefulness")
        if assistant is not None:
            return assistant
        context_score = dashboard_context_downstream_score(result)
        if context_score is not None:
            return context_score
        return average([score_bool(result.get("parsedOk")), score_bool(metrics.get("schema_ok"))])
    if metric_id == "parsed_ok":
        return score_bool(result.get("parsedOk"))
    if metric_id == "schema_ok":
        return score_bool(metrics.get("schema_ok"))
    if metric_id == "must_survive_preserved":
        if "baseline_preservation_pass" in metrics:
            return score_bool(metrics.get("baseline_preservation_pass"))
        related = result_metric_number(result, "related_count")
        refs = result_metric_number(result, "source_ref_count")
        parsed_output = result.get("parsedOutput")
        has_structured_output = isinstance(parsed_output, dict) and bool(parsed_output)
        if refs is not None and refs > 0 and (has_structured_output or (related or 0) > 0):
            return 5.0
        if result.get("parsedOk") is True and metrics.get("schema_ok") is True:
            return 4.0 if refs else 3.5
        if related is None and refs is None and not has_structured_output:
            return None
        return 0.0
    if metric_id == "must_reject_removed":
        return 5.0 if reject_signal_count(result) == 0 else 0.0
    if metric_id == "trace_complete":
        return min(5.0, trace_count(result) / len(TRACE_KEYS) * 5)
    if metric_id == "contract_violation_count":
        return 5.0 if contract_violation_count(result) == 0 else 0.0
    if metric_id in {"semantic_coverage", "source_grounding", "contract_discipline", "completion_fit", "breadth_vs_budget"}:
        return assistant_score(data, case_id, variant_id, metric_id)
    return None


def raw_value_for_metric(result: dict[str, object], metric_id: str) -> float | None:
    if metric_id == "input_tokens":
        return token_number(result, "input_tokens")
    if metric_id == "output_tokens":
        return token_number(result, "output_tokens")
    if metric_id == "duration_ms":
        return result_metric_number(result, "duration_ms") or number_value(result.get("durationMs"))
    if metric_id == "cost_estimate":
        return cost_number(result)
    return None


def format_display(value: float | None, metric_id: str, score: float | None) -> str:
    def format_score_out_of_five(score_value: float) -> str:
        rounded = round(score_value, 1)
        label = str(int(rounded)) if rounded.is_integer() else f"{rounded:.1f}".replace(".", ",")
        return f"{label} von 5"

    if metric_id == "trace_complete" and score is not None:
        return format_score_out_of_five(score)
    if metric_id == "contract_violation_count":
        return "0" if score == 5 else "Bruch"
    if metric_id in {"input_tokens", "output_tokens"} and value is not None:
        return f"{int(value):,}".replace(",", ".")
    if metric_id == "duration_ms" and value is not None:
        return f"{value / 1000:.1f} s"
    if metric_id == "cost_estimate" and value is not None:
        return f"{value:.4f}"
    if score is None:
        return "n/a"
    return format_score_out_of_five(score)


def build_metric_matrix(data: dict[str, object]) -> list[dict[str, object]]:
    variants = [item for item in data.get("variants", []) if isinstance(item, dict)]
    variant_ids = [str(item.get("id")) for item in variants if item.get("id")]
    rows: list[dict[str, object]] = []
    for definition in MATRIX_ROWS:
        metric_id = definition["id"]
        values: dict[str, object] = {}
        for variant_id in variant_ids:
            scores: list[float | None] = []
            raw_values: list[float | None] = []
            for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
                if not isinstance(case, dict):
                    continue
                case_id = str(case.get("id") or "")
                result = next(
                    (
                        item
                        for item in case.get("results", [])
                        if isinstance(item, dict) and str(item.get("variantId")) == variant_id
                    ),
                    None,
                )
                if result is None:
                    continue
                scores.append(score_for_metric(data, case_id, variant_id, result, metric_id))
                raw_values.append(raw_value_for_metric(result, metric_id))
            score = average(scores)
            raw_value = average(raw_values)
            values[variant_id] = {
                "score": round(score, 3) if score is not None else None,
                "rawValue": round(raw_value, 6) if raw_value is not None else None,
                "display": format_display(raw_value, metric_id, score),
                "status": status_from_score(score),
            }
        rows.append({**definition, "values": values})
    return rows


def row_value(row: dict[str, object], variant_id: str, key: str) -> float | None:
    values = row.get("values")
    if not isinstance(values, dict):
        return None
    variant_value = values.get(variant_id)
    if not isinstance(variant_value, dict):
        return None
    return number_value(variant_value.get(key))


def is_guardrail_blocked(row: dict[str, object], variant_id: str) -> bool:
    value = row_value(row, variant_id, "score")
    return value is not None and value < 4.9


def build_assistant_recommendation(data: dict[str, object], metric_matrix: list[dict[str, object]]) -> dict[str, object]:
    variant_ids = [str(item.get("id")) for item in data.get("variants", []) if isinstance(item, dict) and item.get("id")]
    left = str(data.get("leftVariantId") or (variant_ids[0] if variant_ids else "A"))
    right = str(data.get("defaultRightVariant") or (variant_ids[-1] if variant_ids else "B"))
    guardrail_rows = [row for row in metric_matrix if row.get("group") == "guardrail"]
    primary_rows = [row for row in metric_matrix if row.get("group") == "primary"]

    blocked_by_variant = {
        variant_id: [str(row.get("id")) for row in guardrail_rows if is_guardrail_blocked(row, variant_id)]
        for variant_id in variant_ids
    }
    primary_scores = {
        variant_id: average([row_value(row, variant_id, "score") for row in primary_rows])
        for variant_id in variant_ids
    }
    eligible = [variant_id for variant_id in variant_ids if not blocked_by_variant.get(variant_id)]
    if not eligible:
        return {
            "provenance": "assistant_recommendation_from_metric_matrix",
            "recommended_variant": "none",
            "recommendation_type": "reject_candidate",
            "confidence": "high",
            "rationale_short": "Keine Variante ist promotefähig, weil Guardrails blockieren.",
            "blocking_guardrails": sorted({item for values in blocked_by_variant.values() for item in values}),
            "hitl_required": True,
        }

    ranked = sorted(
        eligible,
        key=lambda variant_id: primary_scores.get(variant_id) if primary_scores.get(variant_id) is not None else -1,
        reverse=True,
    )
    best = ranked[0]
    best_score = primary_scores.get(best)
    runner_up_score = primary_scores.get(ranked[1]) if len(ranked) > 1 else None
    if best_score is None:
        return {
            "provenance": "assistant_recommendation_from_metric_matrix",
            "recommended_variant": "inconclusive",
            "recommendation_type": "rerun_needed",
            "confidence": "low",
            "rationale_short": "Die Guardrails reichen für eine fachliche Empfehlung nicht aus; Primary-Evidence fehlt.",
            "blocking_guardrails": blocked_by_variant.get(right, []),
            "hitl_required": True,
        }

    margin = best_score - runner_up_score if runner_up_score is not None else best_score
    confidence = "high" if margin >= 1 else "medium" if margin >= 0.35 else "low"
    if confidence == "low" and runner_up_score is not None:
        return {
            "provenance": "assistant_recommendation_from_metric_matrix",
            "recommended_variant": "inconclusive",
            "recommendation_type": "hitl_required",
            "confidence": "low",
            "rationale_short": "Die fachliche Differenz ist zu knapp für eine automatische Empfehlung.",
            "blocking_guardrails": blocked_by_variant.get(right, []),
            "hitl_required": True,
        }

    recommendation_type = "keep_baseline" if best == left else "promote_candidate" if best == right else "iterate_candidate"
    rationale = (
        "Baseline bleibt nach Primary- und Guardrail-Sicht stärker."
        if best == left
        else "Die Kandidatenvariante erfüllt die Primary-Metriken besser und ist nicht durch Guardrails blockiert."
        if best == right
        else "Eine andere geprüfte Variante liegt vorn; HITL muss entscheiden, ob sie weiterverfolgt wird."
    )
    return {
        "provenance": "assistant_recommendation_from_metric_matrix",
        "recommended_variant": best,
        "recommendation_type": recommendation_type,
        "confidence": confidence,
        "rationale_short": rationale,
        "blocking_guardrails": blocked_by_variant.get(best, []),
        "hitl_required": True,
    }


def build_decision_scorecard(data: dict[str, object], metric_matrix: list[dict[str, object]], recommendation: dict[str, object]) -> dict[str, object]:
    right = str(data.get("defaultRightVariant") or recommendation.get("recommended_variant") or "")
    right_guardrail_blocks = [
        str(row.get("id"))
        for row in metric_matrix
        if row.get("group") == "guardrail" and right and is_guardrail_blocked(row, right)
    ]
    trace_rows = [row for row in metric_matrix if row.get("id") == "trace_complete"]
    trace_status = "green"
    for row in trace_rows:
        values = row.get("values")
        if isinstance(values, dict):
            for value in values.values():
                if isinstance(value, dict) and value.get("status") != "green":
                    trace_status = "red"
    trace_integrity = data.get("traceIntegrity") if isinstance(data.get("traceIntegrity"), dict) else {}
    if trace_integrity.get("status") == "fail":
        trace_status = "red"
    preflight = data.get("preflightChecks") if isinstance(data.get("preflightChecks"), dict) else {}
    preflight_status = str(preflight.get("status") or "neutral")
    reviewer_attention = list(right_guardrail_blocks)
    if trace_status == "red":
        reviewer_attention.append("traceIntegrity prüfen")
    if preflight_status in {"yellow", "red"}:
        reviewer_attention.append("preflightChecks prüfen")
    if not reviewer_attention:
        reviewer_attention = ["assistant_recommendation prüfen", "fachliche Plausibilität gegen Output lesen"]
    primary_status = "neutral"
    recommended = recommendation.get("recommended_variant")
    if isinstance(recommended, str) and recommended not in {"none", "inconclusive"}:
        primary_values = [
            row_value(row, recommended, "score")
            for row in metric_matrix
            if row.get("group") == "primary"
        ]
        primary_status = status_from_score(average(primary_values))
    return {
        "provenance": "derived_from_metric_matrix",
        "primary": {
            "status": primary_status,
            "summary": recommendation.get("rationale_short"),
            "recommendedVariant": recommendation.get("recommended_variant"),
        },
        "guardrails": {
            "status": "red" if right_guardrail_blocks else "green",
            "blockingGuardrails": right_guardrail_blocks,
        },
        "monitoring": {
            "status": "info",
            "summary": "Monitoring erklärt Tokens, Laufzeit und Kosten; es entscheidet die Promotion nur bei expliziten Budget-Experimenten.",
        },
        "evidenceCompleteness": {
            "status": trace_status,
            "summary": "Trace-Vollständigkeit basiert auf den sechs Lab-Runner-Artefakten.",
        },
        "decisionState": {
            "status": "hitl_required",
            "summary": "Assistant Recommendation ist Entscheidungshilfe; Promotion bleibt HITL.",
        },
        "reviewerAttention": reviewer_attention,
    }


def duration_ms(result: dict[str, object] | None) -> float | None:
    if not isinstance(result, dict):
        return None
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return number_value(metrics.get("duration_ms")) or number_value(result.get("durationMs"))


def format_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value / 1000:.1f}s"


def count_label(value: int, total: int) -> str:
    return f"{value}/{total}"


def variant_display_name(data: dict[str, object], variant_id: str) -> str:
    variants = data.get("variants")
    if isinstance(variants, list):
        for variant in variants:
            if isinstance(variant, dict) and str(variant.get("id")) == variant_id:
                return str(
                    variant.get("providerDisplayName")
                    or variant.get("displayName")
                    or variant.get("label")
                    or variant_id
                )
    return variant_id


def result_for_variant(case: dict[str, object], variant_id: str) -> dict[str, object] | None:
    for result in case.get("results", []) if isinstance(case.get("results"), list) else []:
        if isinstance(result, dict) and str(result.get("variantId")) == variant_id:
            return result
    return None


def variant_stats(data: dict[str, object], variant_id: str) -> dict[str, object]:
    results = []
    for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
        if not isinstance(case, dict):
            continue
        result = result_for_variant(case, variant_id)
        if result is not None:
            results.append(result)
    durations = sorted(value for value in (duration_ms(result) for result in results) if value is not None)
    median = None
    if durations:
        mid = len(durations) // 2
        median = durations[mid] if len(durations) % 2 else (durations[mid - 1] + durations[mid]) / 2
    trace_ok = 0
    for result in results:
        trace = result.get("trace") if isinstance(result.get("trace"), dict) else {}
        hashes = trace.get("artifactSha256") if isinstance(trace.get("artifactSha256"), dict) else {}
        if all(hashes.get(key) for key in TRACE_KEYS):
            trace_ok += 1
    return {
        "count": len(results),
        "provider_ok": sum(1 for result in results if not result.get("error")),
        "parse_ok": sum(1 for result in results if result.get("parsedOk") is True),
        "schema_ok": sum(1 for result in results if isinstance(result.get("metrics"), dict) and result["metrics"].get("schema_ok") is True),
        "under_10s": sum(1 for result in results if (duration_ms(result) or float("inf")) <= 10_000),
        "trace_ok": trace_ok,
        "median_ms": median,
        "max_ms": durations[-1] if durations else None,
    }


def metric_row_definition(metric_id: str) -> dict[str, object] | None:
    for row in MATRIX_ROWS:
        if row.get("id") == metric_id:
            return row
    return None


def decision_metric_axes() -> list[dict[str, object]]:
    axes: list[dict[str, object]] = []
    for metric_id in DECISION_METRIC_AXIS_ORDER:
        definition = metric_row_definition(metric_id) or {}
        meta = DECISION_METRIC_AXIS_META.get(metric_id, {})
        axes.append(
            {
                "id": metric_id,
                "label": meta.get("label") or definition.get("label") or metric_id,
                "shortLabel": meta.get("shortLabel") or definition.get("label") or metric_id,
                "chartLabel": meta.get("chartLabel") or meta.get("shortLabel") or definition.get("label") or metric_id,
                "listLabel": meta.get("listLabel") or meta.get("shortLabel") or definition.get("label") or metric_id,
                "description": meta.get("description") or definition.get("meaning") or "",
            }
        )
    return axes


def variant_short_label_for_index(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return alphabet[index] if 0 <= index < len(alphabet) else f"V{index + 1}"


def variant_short_label(data: dict[str, object], variant_id: str) -> str:
    variants = data.get("variants")
    if isinstance(variants, list):
        for index, variant in enumerate(variants):
            if isinstance(variant, dict) and str(variant.get("id")) == variant_id:
                label = variant.get("variantShortLabel") or variant.get("shortLabel")
                return str(label or variant_short_label_for_index(index))
    return variant_id.split("_", 1)[0] or variant_id


def metric_source_count(result: dict[str, object]) -> int:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return int(metrics.get("source_ref_count") or 0)


def metric_content_count(result: dict[str, object]) -> int:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return int(metrics.get("content_character_count") or metrics.get("markdown_character_count") or 0)


def metric_value_text(result: dict[str, object] | None, metric_id: str, score: float | None) -> str:
    if not isinstance(result, dict):
        return "Kein Resultat vorhanden."
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    if metric_id == "round_goal_fit":
        if has_metric(result, "dashboard_context_score"):
            return (
                f"Dashboard-Kontext {format_display(dashboard_context_score(result), metric_id, dashboard_context_score(result))}, "
                f"Kernfelder {'erhalten' if metrics.get('baseline_preservation_pass') is True else 'offen'}"
            )
        return (
            f"{format_seconds(duration_ms(result))} Laufzeit, "
            f"Parse {'ok' if result.get('parsedOk') is True else 'offen'}, "
            f"Schema {'ok' if metrics.get('schema_ok') is True else 'offen'}"
        )
    if metric_id == "thesis_aligned_output_quality":
        context_score = dashboard_context_score(result)
        if context_score is not None:
            return f"dashboard_context_score {format_display(context_score, metric_id, context_score)}"
        content = metric_content_count(result)
        sources = metric_source_count(result)
        if content:
            return f"{content:,}".replace(",", ".") + f" Content-Zeichen, {sources} Quellen"
        return f"{sources} Quellen"
    if metric_id == "downstream_usefulness":
        if "dashboard_context_present" in metrics:
            if metrics.get("dashboard_context_present") is True:
                return "Dashboard-Kontext vorhanden und für Stage 00b nutzbar"
            return "Kein dashboard_page_context für Stage 00b"
        related = int(metrics.get("related_count") or 0)
        sources = metric_source_count(result)
        return f"{related} Related-Signale, {sources} Quellen"
    if metric_id == "contract_violation_count":
        return f"{contract_violation_count(result)} Vertragsbrüche"
    if metric_id == "parsed_ok":
        return "parsebar" if result.get("parsedOk") is True else "nicht parsebar"
    if metric_id == "schema_ok":
        return "schema-ok" if metrics.get("schema_ok") is True else "schema offen"
    if metric_id == "must_survive_preserved":
        if "baseline_preservation_pass" in metrics:
            return "Kernfelder relativ zur Baseline erhalten" if metrics.get("baseline_preservation_pass") is True else "Kernfelder gegenüber der Baseline verschoben"
        return f"{format_display(None, metric_id, score)} Kernsignale erhalten"
    if metric_id == "must_reject_removed":
        return f"{reject_signal_count(result)} Reject-Signale"
    if metric_id == "trace_complete":
        return f"{trace_count(result)}/{len(TRACE_KEYS)} Trace-Artefakte"
    raw_value = raw_value_for_metric(result, metric_id)
    return format_display(raw_value, metric_id, score)


def metric_interpretation_text(data: dict[str, object], variant_id: str, metric_id: str) -> str:
    label = variant_short_label(data, variant_id)
    texts = {
        "round_goal_fit": f"{label} erfüllt das Rundenziel, wenn Primary-Signale und harte Guardrails zusammen tragen.",
        "thesis_aligned_output_quality": f"{label} wird danach bewertet, ob die Antwort die getestete These wirklich stützt.",
        "downstream_usefulness": f"{label} ist downstream nützlich, wenn die nächste Stufe ohne manuelle Reparatur weiterarbeiten kann.",
        "contract_violation_count": f"{label} sollte keine Reparatur nach der Modellantwort brauchen. Weniger Verletzungen ergeben den besseren Score.",
        "parsed_ok": f"{label} muss einen Output liefern, den der Review-Parser ohne Rettungsversuch lesen kann.",
        "schema_ok": f"{label} muss den erwarteten Output-Vertrag erfüllen.",
        "must_survive_preserved": f"{label} muss die Kernsignale der Runde erhalten.",
        "must_reject_removed": f"{label} darf keine Beispielreste, Citation-Altlasten oder offensichtliche Contract-Leaks tragen.",
        "trace_complete": f"{label} muss über Request, Prompt, Response, Parsed Output und Metrics zurückverfolgbar bleiben.",
    }
    return texts.get(metric_id, f"{label} wird gegen diese Metrik als Review-Evidence gelesen.")


def decision_metric_variant_bundle(data: dict[str, object], case_id: str, variant_id: str, result: dict[str, object] | None) -> dict[str, object]:
    scores: dict[str, object] = {}
    values: dict[str, object] = {}
    interpretations: dict[str, object] = {}
    for axis in decision_metric_axes():
        metric_id = str(axis["id"])
        score = score_for_metric(data, case_id, variant_id, result, metric_id) if isinstance(result, dict) else None
        scores[metric_id] = round(score, 3) if score is not None else None
        values[metric_id] = metric_value_text(result, metric_id, score)
        interpretations[metric_id] = metric_interpretation_text(data, variant_id, metric_id)
    return {
        "scores": scores,
        "values": values,
        "interpretations": interpretations,
    }


def decision_metric_status(score: object) -> str:
    return status_from_score(number_value(score))


def decision_metric_guardrails(right_bundle: dict[str, object]) -> list[dict[str, object]]:
    scores = right_bundle.get("scores") if isinstance(right_bundle.get("scores"), dict) else {}
    values = right_bundle.get("values") if isinstance(right_bundle.get("values"), dict) else {}
    guardrail_ids = [
        "parsed_ok",
        "schema_ok",
        "contract_violation_count",
        "must_survive_preserved",
        "must_reject_removed",
        "trace_complete",
    ]
    items = []
    for metric_id in guardrail_ids:
        meta = DECISION_METRIC_AXIS_META.get(metric_id, {})
        score = scores.get(metric_id) if isinstance(scores, dict) else None
        items.append(
            {
                "axisId": metric_id,
                "title": str(meta.get("listLabel") or meta.get("shortLabel") or meta.get("label") or metric_id),
                "status": decision_metric_status(score),
                "text": str(values.get(metric_id) or "n/a"),
            }
        )
    return items


def decision_metric_monitoring(data: dict[str, object], case: dict[str, object], right_variant_id: str) -> list[dict[str, object]]:
    right = result_for_variant(case, right_variant_id)
    if not isinstance(right, dict):
        return []
    items = []
    for row in MATRIX_ROWS:
        if row.get("group") != "monitoring":
            continue
        metric_id = str(row.get("id") or "")
        raw_value = raw_value_for_metric(right, metric_id)
        score = score_for_metric(data, str(case.get("id") or ""), right_variant_id, right, metric_id)
        display = format_display(raw_value, metric_id, score)
        items.append(
            {
                "id": metric_id,
                "title": str(row.get("label") or metric_id),
                "status": status_from_score(score),
                "text": display,
            }
        )
    return items


def build_decision_metrics(data: dict[str, object]) -> dict[str, object]:
    variant_ids = [str(item.get("id")) for item in data.get("variants", []) if isinstance(item, dict) and item.get("id")]
    if not variant_ids:
        return {}
    left = str(data.get("leftVariantId") or variant_ids[0])
    right = str(data.get("defaultRightVariant") or variant_ids[-1])
    axes = decision_metric_axes()
    case_bundles: dict[str, object] = {}
    for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("id") or "")
        if not case_id:
            continue
        variant_bundles = {}
        for variant_id in variant_ids:
            variant_bundles[variant_id] = decision_metric_variant_bundle(
                data,
                case_id,
                variant_id,
                result_for_variant(case, variant_id),
            )
        right_bundle = variant_bundles.get(right) if isinstance(variant_bundles.get(right), dict) else {}
        right_scores = right_bundle.get("scores") if isinstance(right_bundle.get("scores"), dict) else {}
        right_name = variant_display_name(data, right)
        primary_sentences = [
            {
                "title": "Rundenziel",
                "status": decision_metric_status(right_scores.get("round_goal_fit")),
                "text": f"{right_name} wird gegen Rundenziel, Guardrails und Trace-Evidence lesbar bewertet.",
            },
            {
                "title": "These",
                "status": decision_metric_status(right_scores.get("thesis_aligned_output_quality")),
                "text": "Die Bewertung trennt sichtbare Outputqualität von bloßer Format- oder Textlängenverbesserung.",
            },
            {
                "title": "Downstream",
                "status": decision_metric_status(right_scores.get("downstream_usefulness")),
                "text": "Die nächste Frage ist, ob der Output in Prompt-Contract, JSON-Vertrag, Runtime oder nächsten Testhebel zurückgeführt werden kann.",
            },
        ]
        case_bundles[case_id] = {
            "title": f"{case.get('companyName') or case_id}: Entscheidungssignale",
            "note": "Diese Scores sind assistant_review-Entscheidungshilfe. Sie entstehen aus den sichtbaren Lab-Artefakten, nicht aus einer neuen Provider-Antwort.",
            "provenance": "assistant_review",
            "primarySentences": primary_sentences,
            "variants": variant_bundles,
            "guardrails": decision_metric_guardrails(right_bundle),
            "monitoring": decision_metric_monitoring(data, case, right),
        }

    return {
        "label": "Metrik-Auswertung",
        "title": "Prompt-A/B: Pflichtmetriken im Spinnennetz",
        "note": "Die primäre Einschätzung steht vorn. Guardrails tauchen nur auf, wenn sie wirklich Aufmerksamkeit brauchen. Radar und Karten sind Entscheidungshilfe, kein automatisches Promotion-Gate.",
        "provenance": "assistant_review",
        "axes": axes,
        "cases": case_bundles,
    }


def merge_decision_metrics(generated: dict[str, object], existing: object) -> dict[str, object]:
    if not isinstance(existing, dict):
        return generated
    merged = {**generated, **existing}
    generated_cases = generated.get("cases") if isinstance(generated.get("cases"), dict) else {}
    existing_cases = existing.get("cases") if isinstance(existing.get("cases"), dict) else {}
    merged["cases"] = {**generated_cases, **existing_cases}
    if not merged.get("axes"):
        merged["axes"] = generated.get("axes", [])
    return merged


def build_goal_progress(data: dict[str, object], recommendation: dict[str, object]) -> dict[str, object]:
    right = str(data.get("defaultRightVariant") or recommendation.get("recommended_variant") or "")
    right_name = variant_display_name(data, right) if right else "Kandidatenvariante"
    stats = variant_stats(data, right) if right else {"count": 0, "schema_ok": 0, "under_10s": 0, "trace_ok": 0}
    total = int(stats.get("count") or 0)
    return {
        "label": "Stand der Zielerreichung",
        "title": "Rundenziel messbar; finale Produktentscheidung bleibt HITL.",
        "summary": (
            "Diese Karte beantwortet, ob die Runde ihrem Ziel näher gekommen ist: "
            "schneller, parsebarer und besser belegbarer Prompt-Output. Sie ersetzt "
            "nicht die fachliche Entscheidung, welche Regeln übernommen werden."
        ),
        "metrics": [
            {"value": count_label(int(stats.get("schema_ok") or 0), total), "label": f"{right_name} schema-ok"},
            {"value": count_label(int(stats.get("under_10s") or 0), total), "label": f"{right_name} unter 10 Sekunden"},
            {"value": count_label(int(stats.get("trace_ok") or 0), total), "label": "Trace vollständig"},
            {"value": str(recommendation.get("recommendation_type") or "hitl_required"), "label": "Entscheidungsstatus"},
        ],
        "items": [
            "Ziel: prüfen, ob ein konkreter Prompt-Hebel über echte Cases bessere, schnellere und belegbarere Ergebnisse liefert.",
            f"Näher am Ziel: {right_name} ist über {total} Cases technisch messbar; Parse, Schema, Laufzeit und Trace stehen getrennt sichtbar.",
            "Noch offen: Semantik, Downstream-Nutzen und Guardrails müssen als Entscheidung gelesen werden, nicht als automatische Promotion.",
            "Nächster Schritt: Case-Endreviews und Overall-Endurteil nutzen, um den nächsten Prompt-, Contract- oder Prozesshebel festzulegen.",
        ],
    }


def build_overall_analysis(data: dict[str, object], recommendation: dict[str, object]) -> dict[str, object]:
    left = str(data.get("leftVariantId") or "")
    right = str(data.get("defaultRightVariant") or recommendation.get("recommended_variant") or "")
    left_name = variant_display_name(data, left) if left else "Baseline"
    right_name = variant_display_name(data, right) if right else "Kandidat"
    left_stats = variant_stats(data, left) if left else {"count": 0}
    right_stats = variant_stats(data, right) if right else {"count": 0}
    right_total = int(right_stats.get("count") or 0)
    left_total = int(left_stats.get("count") or 0)
    return {
        "label": "Overall-Endurteil",
        "title": "Gesamtbefund über alle Cases",
        "summary": (
            f"{left_name} und {right_name} werden über dieselben Cases gelesen. "
            "Wichtig ist nicht nur, welche Variante gewinnt, sondern ob das Ergebnis "
            "stabil genug ist, um daraus den nächsten Iterationsschritt abzuleiten."
        ),
        "metrics": [
            {"value": count_label(int(left_stats.get("schema_ok") or 0), left_total), "label": f"{left_name} schema-ok"},
            {"value": count_label(int(right_stats.get("schema_ok") or 0), right_total), "label": f"{right_name} schema-ok"},
            {"value": format_seconds(number_value(right_stats.get("median_ms"))), "label": f"{right_name} Median"},
            {"value": str(recommendation.get("confidence") or "n/a"), "label": "Empfehlungs-Konfidenz"},
        ],
        "items": [
            f"{left_name}: {count_label(int(left_stats.get('parse_ok') or 0), left_total)} parsebar, {count_label(int(left_stats.get('trace_ok') or 0), left_total)} mit vollständigem Trace.",
            f"{right_name}: {count_label(int(right_stats.get('parse_ok') or 0), right_total)} parsebar, {count_label(int(right_stats.get('trace_ok') or 0), right_total)} mit vollständigem Trace.",
            f"Assistant Recommendation: {recommendation.get('recommendation_type') or 'hitl_required'}; {recommendation.get('rationale_short') or 'keine Kurzbegründung hinterlegt'}",
            "HITL-Fokus: Welche Erkenntnisse werden in Prompt, JSON-Vertrag, Runtime/UI oder nächste Testvariante zurückgeführt?",
        ],
    }


def build_interpretation_notes(data: dict[str, object], recommendation: dict[str, object]) -> dict[str, object]:
    recommended = recommendation.get("recommended_variant")
    notes: dict[str, object] = {
        "primary": [
            recommendation.get("rationale_short") or "Keine belastbare Primary-Interpretation vorhanden.",
            "Primary bewertet das Rundenziel neutral: A kann gewinnen, B kann gewinnen, oder keine Variante ist promotefähig.",
        ],
        "guardrails": [
            "Rote Guardrails blockieren Promotion auch dann, wenn Primary-Metriken gut aussehen.",
            "Parse, Schema, Must-Survive, Must-Reject, Trace und Vertragsbrüche bleiben getrennt prüfbar.",
        ],
        "monitoring": [
            "Monitoring zeigt Aufwand und Nebenwirkungen, ist aber kein Qualitätsbeweis.",
        ],
        "assistant_review": [
            "Assistant Review ist qualitative Entscheidungshilfe und bleibt von Runtime- und Provider-Metriken getrennt.",
        ],
        "assistant_recommendation": {
            "recommended_variant": recommended,
            "summary": recommendation.get("rationale_short"),
            "hitl_required": True,
        },
    }
    left = str(data.get("leftVariantId") or "")
    right = str(data.get("defaultRightVariant") or recommended or "")
    for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("id") or "")
        if not case_id:
            continue
        left_result = result_for_variant(case, left) if left else None
        right_result = result_for_variant(case, right) if right else None
        left_name = variant_display_name(data, left) if left else "A"
        right_name = variant_display_name(data, right) if right else "B"
        right_metrics = right_result.get("metrics") if isinstance(right_result, dict) and isinstance(right_result.get("metrics"), dict) else {}
        notes[case_id] = {
            "lede": f"A und B werden für denselben Case gelesen. Entscheidend ist, ob {right_name} das Rundenziel besser erfüllt und downstream ohne Reparatur nutzbar bleibt.",
            "leftTitle": f"Was {left_name} zeigt",
            "a": f"Parse: {bool(left_result and left_result.get('parsedOk'))}; Laufzeit: {format_seconds(duration_ms(left_result))}.",
            "rightTitle": f"Was {right_name} zeigt",
            "variants": {
                right: f"Parse: {bool(right_result and right_result.get('parsedOk'))}; Schema: {bool(right_metrics.get('schema_ok'))}; Laufzeit: {format_seconds(duration_ms(right_result))}."
            },
            "verdict": recommendation.get("rationale_short") or "Urteil offen: Die Runde liefert Evidence, aber keine automatische Promotion.",
            "contentTitle": "Was wir im Chat klären müssen",
            "content": [
                "Rundenziel: Ist die Kandidatenvariante wirklich näher am Ziel oder nur besser formatiert?",
                "Evidence: Welche sichtbaren Quellen, Metriken oder Trace-Artefakte stützen die Empfehlung, und welche fehlen?",
                "Downstream: Kann die nächste Stufe den Output ohne Reparatur verwenden?",
                "Rückführung: Gehört die Erkenntnis in den Prompt-Contract, den JSON-Vertrag, den UI-/Runtime-Flow oder nur in die nächste Testvariante?",
            ],
            "riskTitle": "Risiko",
            "risk": "Parse- und Schema-Erfolg beweisen noch keine fachliche Qualität; Guardrails und Must-Survive-Facts bleiben separat zu prüfen.",
            "nextTitle": "Nächster sinnvoller Schritt",
            "next": "Diesen Case gegen Ziel, Evidence, Downstream und Rückführung lesen und die Entscheidung im Round-Ledger festhalten.",
        }
    return notes


def build_preflight_checks(data: dict[str, object], external_reports: list[dict[str, object]] | None = None) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("id") or "")
        for result in case.get("results", []) if isinstance(case.get("results"), list) else []:
            if not isinstance(result, dict):
                continue
            checks.append(build_preflight_for_result(result, case_id, str(result.get("variantId") or "")))

    summary = summarize_preflight(checks)
    if external_reports:
        summary["externalReports"] = external_reports
    return summary


def technical_gate_pass(result: dict[str, object]) -> bool:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return (
        result.get("parsedOk") is True
        and metrics.get("schema_ok") is True
        and trace_count(result) == len(TRACE_KEYS)
    )


def result_has_metric_family(data: dict[str, object], metric_name: str) -> bool:
    for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
        if not isinstance(case, dict):
            continue
        for result in case.get("results", []) if isinstance(case.get("results"), list) else []:
            if not isinstance(result, dict):
                continue
            metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
            if metric_name in metrics:
                return True
    return False


def scorecard_count_for_variant(data: dict[str, object], variant_id: str, predicate: str) -> tuple[int, int]:
    total = 0
    passed = 0
    for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
        if not isinstance(case, dict):
            continue
        result = result_for_variant(case, variant_id)
        if not isinstance(result, dict):
            continue
        total += 1
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
        if predicate == "technical":
            ok = technical_gate_pass(result)
        elif predicate == "dashboard_context":
            ok = metrics.get("dashboard_context_present") is True and metrics.get("dashboard_context_pass") is True
        elif predicate == "target_block_goal":
            ok = metrics.get("target_block_goal_pass") is True
        else:
            ok = False
        if ok:
            passed += 1
    return passed, total


def build_scorecards(data: dict[str, object]) -> list[dict[str, object]]:
    variants = [str(item.get("id")) for item in data.get("variants", []) if isinstance(item, dict) and item.get("id")]
    if len(variants) < 2:
        return []

    left = str(data.get("leftVariantId") or variants[0])
    right = str(data.get("defaultRightVariant") or variants[-1])
    left_label = variant_short_label(data, left)
    right_label = variant_short_label(data, right)

    left_technical = scorecard_count_for_variant(data, left, "technical")
    right_technical = scorecard_count_for_variant(data, right, "technical")
    scorecards = [
        {"value": count_label(*left_technical), "label": f"{left_label} technische Gates"},
        {"value": count_label(*right_technical), "label": f"{right_label} technische Gates"},
    ]

    if result_has_metric_family(data, "dashboard_context_present"):
        left_context = scorecard_count_for_variant(data, left, "dashboard_context")
        right_context = scorecard_count_for_variant(data, right, "dashboard_context")
        scorecards.extend(
            [
                {"value": count_label(*left_context), "label": f"{left_label} Dashboard-Kontext"},
                {"value": count_label(*right_context), "label": f"{right_label} Dashboard-Kontext"},
            ]
        )
    else:
        left_goal = scorecard_count_for_variant(data, left, "target_block_goal")
        right_goal = scorecard_count_for_variant(data, right, "target_block_goal")
        scorecards.extend(
            [
                {"value": count_label(*left_goal), "label": f"{left_label} Ziel-Fit"},
                {"value": count_label(*right_goal), "label": f"{right_label} Ziel-Fit"},
            ]
        )

    return scorecards


def attach_decision_support(data: dict[str, object], external_preflight: list[dict[str, object]] | None = None) -> None:
    data["traceIntegrity"] = build_trace_integrity(data)
    data["preflightChecks"] = build_preflight_checks(data, external_preflight)
    metric_matrix = build_metric_matrix(data)
    recommendation = build_assistant_recommendation(data, metric_matrix)
    data["metricMatrix"] = metric_matrix
    data["assistant_recommendation"] = recommendation
    data["assistantRecommendation"] = recommendation
    data["decisionScorecard"] = build_decision_scorecard(data, metric_matrix, recommendation)
    data["decisionMetrics"] = merge_decision_metrics(build_decision_metrics(data), data.get("decisionMetrics"))
    data.setdefault("scorecards", build_scorecards(data))
    data.setdefault("goalProgress", build_goal_progress(data, recommendation))
    data.setdefault("overallAnalysis", build_overall_analysis(data, recommendation))
    existing_notes = data.get("interpretationNotes")
    generated_notes = build_interpretation_notes(data, recommendation)
    if isinstance(existing_notes, dict):
        data["interpretationNotes"] = {**generated_notes, **existing_notes}
    else:
        data["interpretationNotes"] = generated_notes
    data.setdefault("hitlDecision", build_hitl_decision())


def build_from_summary(summary: dict[str, object], summary_path: Path | None = None) -> dict[str, object]:
    variants = summary.get("variants", [])
    variant_ids = [str(item.get("id")) for item in variants if isinstance(item, dict) and item.get("id")]
    variant_short_labels = {}
    for index, variant_id in enumerate(variant_ids):
        variant = next((item for item in variants if isinstance(item, dict) and str(item.get("id")) == variant_id), {})
        variant_short_labels[variant_id] = str(
            variant.get("variantShortLabel")
            or variant.get("shortLabel")
            or variant_short_label_for_index(index)
        )
    cases = summary.get("cases", [])
    results = summary.get("results", [])
    by_case: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in results if isinstance(results, list) else []:
        if isinstance(item, dict):
            by_case[str(item.get("case_id") or item.get("caseId") or "")].append(item)

    surface_cases = []
    for case in cases if isinstance(cases, list) else []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("id"))
        surface_results = []
        for item in by_case.get(case_id, []):
            variant_id = str(item.get("variant_id") or item.get("variantId"))
            provider_meta = provider_metadata(item, summary_path)
            surface_results.append(
                {
                    "caseId": case_id,
                    "variantId": variant_id,
                    "variantShortLabel": variant_short_labels.get(variant_id) or variant_id.split("_", 1)[0],
                    "variantLabel": item.get("variant_label") or item.get("variantLabel") or variant_id,
                    "providerRoute": item.get("provider_route") or item.get("providerRoute"),
                    "providerCalledAt": provider_meta["providerCalledAt"],
                    "model": provider_meta["model"],
                    "tokenUsage": provider_meta["tokenUsage"],
                    "maxOutputTokens": provider_meta["maxOutputTokens"],
                    "durationMs": item.get("duration_ms") or item.get("durationMs"),
                    "parsedOk": item.get("parsed_ok") if "parsed_ok" in item else item.get("parsedOk"),
                    "parseError": item.get("parse_error") or item.get("parseError"),
                    "metrics": item.get("metrics") or {},
                    "prompt": prompt_from_artifacts(item, summary_path),
                    "responseText": response_text_from_artifacts(item, summary_path),
                    "parsedOutput": item.get("parsed_output") or item.get("parsedOutput"),
                    "artifactBase": item.get("artifact_base") or item.get("artifactBase"),
                    "trace": artifact_trace(item, summary_path),
                }
            )
        metadata = case.get("metadata") if isinstance(case.get("metadata"), dict) else {}
        test_intent = (
            case.get("testIntent")
            or case.get("test_intent")
            or metadata.get("testIntent")
            or metadata.get("test_intent")
        )
        surface_case = {
            "id": case_id,
            "companyName": case.get("companyName") or case.get("company_name") or case_id,
            "results": surface_results,
        }
        if metadata:
            surface_case["metadata"] = metadata
        if isinstance(test_intent, dict):
            surface_case["testIntent"] = test_intent
        surface_cases.append(surface_case)

    left = variant_ids[0] if variant_ids else "A_current"
    right = variant_ids[-1] if len(variant_ids) > 1 else "B_candidate"
    review_data = {
        "title": summary.get("experiment") or "Pre-Spec Prompt A/B Review",
        "kicker": "Pre-Spec Prompt Review",
        "heroTitleHtml": "Prompt-Runde: <em>A gegen B</em>",
        "lede": "Kompaktes Briefing für Prompt-Contract, echte Provider-Rückgabe, Review-Metriken und HITL-Entscheidung.",
        "evidenceClass": summary.get("evidence_class") or "pre_spec_prompt_ab",
        "leftVariantId": left,
        "defaultCaseId": surface_cases[0]["id"] if surface_cases else "",
        "defaultRightVariant": right,
        "sourcePromptContract": summary.get("source_prompt_contract"),
        "sourceFoundation": summary.get("source_foundation"),
        "testsetSource": summary.get("testset_source"),
        "outputViewMode": "tree_only",
        "outputTreeDefaultExpanded": "all",
        "copy": {
            "promptSectionNote": "A und B werden als vollständige Run-Lanes gelesen: System-Prompt, User-Prompt, LLM-Antwort und Evidenz stehen jeweils direkt zusammen.",
            "outputSectionNote": "Die Outputs stammen aus den jeweiligen Lab-Artefakten; Raw Prompt, Response und Parsed Output bleiben prüfbar.",
            "interpretationSectionNote": "Das Endurteil bleibt HITL: Die Fläche zeigt, was technisch trägt und welche fachlichen Fragen noch entschieden werden müssen.",
        },
        "recommendation": {
            "label": "Empfehlung",
            "title": "HITL-Entscheidung erforderlich",
            "body": "Die HTML-Fläche visualisiert Evidence. Die Entscheidung bleibt im Markdown-Ledger.",
        },
        "notProven": {
            "label": "Nicht bewiesen",
            "items": summary.get("not_proven") or ["production_readiness"],
        },
        "variants": variants,
        "cases": surface_cases,
        "interpretationNotes": {},
        "hitlDecision": build_hitl_decision(summary),
    }
    passthrough_fields = {
        "goal_progress": "goalProgress",
        "goalProgress": "goalProgress",
        "overall_analysis": "overallAnalysis",
        "overallAnalysis": "overallAnalysis",
        "decision_metrics": "decisionMetrics",
        "decisionMetrics": "decisionMetrics",
        "interpretation_notes": "interpretationNotes",
        "interpretationNotes": "interpretationNotes",
        "iteration_path": "iterationPath",
        "iterationPath": "iterationPath",
        "round_navigation": "roundNavigation",
        "roundNavigation": "roundNavigation",
        "source_links": "sourceLinks",
        "sourceLinks": "sourceLinks",
        "scorecards": "scorecards",
        "test_intent": "testIntent",
        "testIntent": "testIntent",
        "test_design": "testDesign",
        "testDesign": "testDesign",
    }
    for source_key, target_key in passthrough_fields.items():
        value = summary.get(source_key)
        if value is not None:
            review_data[target_key] = value
    if isinstance(summary.get("assistant_evaluation"), dict):
        review_data["assistantEvaluation"] = summary["assistant_evaluation"]
    if isinstance(summary.get("iteration_path"), list):
        review_data["iterationPath"] = summary["iteration_path"]
    external_preflight = summary.get("preflight_checks") or summary.get("preflightChecks")
    attach_decision_support(review_data, external_preflight if isinstance(external_preflight, list) else None)
    return review_data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--assistant-evaluation", type=Path)
    parser.add_argument("--iteration-path", type=Path)
    parser.add_argument("--preflight", action="append", type=Path, help="Optional deterministic preflight report JSON.")
    args = parser.parse_args()

    summary = load_json(args.results)
    if not isinstance(summary, dict):
        raise SystemExit("results summary must be a JSON object")
    if args.assistant_evaluation:
        evaluation = load_json(args.assistant_evaluation)
        if not isinstance(evaluation, dict):
            raise SystemExit("assistant evaluation must be a JSON object")
        summary["assistant_evaluation"] = evaluation
    if args.iteration_path:
        iteration_path = load_json(args.iteration_path)
        if not isinstance(iteration_path, list):
            raise SystemExit("iteration path must be a JSON array")
        summary["iteration_path"] = iteration_path
    if args.preflight:
        preflight_reports = []
        for path in args.preflight:
            report = load_json(path)
            if not isinstance(report, dict):
                raise SystemExit(f"preflight report must be a JSON object: {path}")
            preflight_reports.append(report)
        summary["preflight_checks"] = preflight_reports
    data = build_from_summary(summary, args.results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
