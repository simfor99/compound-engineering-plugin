#!/usr/bin/env python3
"""Run an autonomous CE Prompt Improver A/B loop from a bounded manifest."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
NON_PASSING_GATE_POLICIES = {"not_claimed", "deferred"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def slug(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in safe.split("-") if part) or "round"


def resolve_path(raw: str | Path, base_dir: Path) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (base_dir / path).resolve()


def resolve_campaign_dir(raw: str | Path, config_dir: Path, repo_root: Path) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    raw_text = str(raw)
    if raw_text.startswith("./") or raw_text.startswith("../"):
        return (config_dir / path).resolve()
    return (repo_root / path).resolve()


def config_bool(value: Any, *, default: bool, field: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    raise ValueError(f"promotion.{field} must be a boolean, not {value!r}")


def config_gate_policy(value: Any, *, default: bool, field: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        if normalized in NON_PASSING_GATE_POLICIES:
            return normalized
        if normalized == "not_applicable":
            return "disabled"
    return "required" if config_bool(value, default=default, field=field) else "disabled"


def validate_promotion_config(promotion: dict[str, Any]) -> None:
    config_gate_policy(promotion.get("requireRealAb"), default=True, field="requireRealAb")
    config_gate_policy(promotion.get("requireSchemaOk"), default=True, field="requireSchemaOk")
    config_gate_policy(promotion.get("requireTraceIntegrity"), default=True, field="requireTraceIntegrity")


def non_passing_gate(gate: str, status: str) -> dict[str, Any]:
    return {
        "gate": gate,
        "status": status,
        "issues": [
            {
                "message": f"promotion gate explicitly marked {status}; not treated as passed evidence",
            }
        ],
    }


def run_command(command: list[str], cwd: Path, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode and not allow_failure:
        raise RuntimeError(
            "Command failed"
            + f"\nexit: {result.returncode}"
            + f"\ncmd: {' '.join(command)}"
            + (f"\nstdout:\n{result.stdout}" if result.stdout else "")
            + (f"\nstderr:\n{result.stderr}" if result.stderr else "")
        )
    return result


def json_from_stdout(result: subprocess.CompletedProcess[str], command_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{command_name} did not emit JSON on stdout:\n{result.stdout}\n{result.stderr}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{command_name} emitted non-object JSON")
    return parsed


def load_report_or_failure(path: Path, gate: str, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        if not path.exists():
            raise FileNotFoundError(path)
        parsed = load_json(path)
        if not isinstance(parsed, dict):
            raise ValueError("report must be a JSON object")
        return parsed
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "fail",
            "issues": [
                {
                    "path": str(path),
                    "message": f"{gate} report unavailable or invalid: {exc}",
                    "exit_code": str(result.returncode),
                }
            ],
        }


def runner_failure_result(
    *,
    case: dict[str, Any],
    variant: dict[str, Any],
    surface: str,
    result: subprocess.CompletedProcess[str],
    called_at: str,
) -> dict[str, Any]:
    case_id = str(case.get("id") or case.get("case_id") or "case")
    variant_id = str(variant["id"])
    error = result.stderr.strip() or result.stdout.strip() or f"{surface} runner exited with {result.returncode}"
    return {
        "case_id": case_id,
        "company_name": case.get("companyName") or case.get("company_name") or case_id,
        "variant_id": variant_id,
        "variant_label": variant.get("label") or variant_id,
        "provider_route": surface,
        "model": None,
        "token_usage": None,
        "max_output_tokens": None,
        "request_without_secret": {},
        "prompt": {"system": "", "user": ""},
        "duration_ms": None,
        "error": error,
        "response_text": "",
        "parsed_ok": False,
        "parsed_output": {},
        "parse_error": "runner_failed_before_json_output",
        "metrics": {
            "provider_error": error,
            "case_id": case_id,
            "variant_id": variant_id,
            "schema_ok": False,
            "runner_exit_code": result.returncode,
        },
        "artifact_base": None,
        "provider_called_at": called_at,
        "runner_exit_code": result.returncode,
        "runner_stdout": result.stdout,
        "runner_stderr": result.stderr,
    }


def normalize_case(case_spec: Any, cases_dir: Path, config_dir: Path) -> dict[str, Any]:
    if isinstance(case_spec, str):
        path = resolve_path(case_spec, config_dir)
        case = load_json(path)
        if not isinstance(case, dict):
            raise ValueError(f"case file must contain an object: {path}")
        case["_source_path"] = str(path)
        return case
    if isinstance(case_spec, dict):
        case = dict(case_spec)
        if "path" in case and len(case) == 1:
            return normalize_case(str(case["path"]), cases_dir, config_dir)
        case_id = str(case.get("id") or case.get("case_id") or "case")
        path = cases_dir / f"{slug(case_id)}.json"
        write_json(path, {key: value for key, value in case.items() if key != "_source_path"})
        case["_source_path"] = str(path)
        return case
    raise ValueError("each case must be a JSON object or path string")


def variant_prompt_paths(variant: dict[str, Any], config_dir: Path) -> tuple[Path, Path]:
    if not isinstance(variant.get("system"), str) or not isinstance(variant.get("user"), str):
        raise ValueError(f"variant {variant.get('id')} needs system and user prompt file paths")
    return resolve_path(str(variant["system"]), config_dir), resolve_path(str(variant["user"]), config_dir)


def result_artifact_prompt_path(result: dict[str, Any]) -> Path | None:
    raw_base = result.get("artifact_base") or result.get("artifactBase")
    if not isinstance(raw_base, str) or not raw_base:
        return None
    base = Path(raw_base)
    prompt = base.with_name(base.name + "__02_rendered-prompt.txt")
    return prompt if prompt.exists() else None


def build_round_navigation(rounds: list[dict[str, Any]], current_round_id: str) -> list[dict[str, Any]]:
    items = []
    for index, item in enumerate(rounds, start=1):
        round_id = str(item["id"])
        nav: dict[str, Any] = {
            "id": round_id,
            "shortLabel": f"R{index:02d}",
            "label": item.get("label") or f"R{index:02d} {round_id}",
            "current": round_id == current_round_id,
        }
        if round_id != current_round_id:
            nav["href"] = f"../../{round_id}/html/index.html"
        items.append(nav)
    return items


def iteration_path_from_rounds(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for index, item in enumerate(rounds, start=1):
        score = item.get("candidateScore")
        score_label = f"{score:.1f}/5" if isinstance(score, (int, float)) else "n/a"
        items.append(
            {
                "title": f"R{index:02d}: {item.get('lever') or item.get('id')}",
                "text": item.get("summary") or item.get("stopReason") or "Autonomous CE Prompt Lab round.",
                "status": "pass" if item.get("accepted") else "executed",
                "impact": f"Candidate score {score_label}",
            }
        )
    return items


def average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def metric_average(data: dict[str, Any], variant_id: str, groups: set[str]) -> float | None:
    scores: list[float] = []
    for row in data.get("metricMatrix", []):
        if not isinstance(row, dict) or str(row.get("group")) not in groups:
            continue
        values = row.get("values")
        bundle = values.get(variant_id) if isinstance(values, dict) else None
        score = number(bundle.get("score")) if isinstance(bundle, dict) else None
        if score is not None:
            scores.append(score)
    return average(scores)


def guardrail_failures(data: dict[str, Any], variant_id: str, min_score: float) -> list[dict[str, Any]]:
    failures = []
    for row in data.get("metricMatrix", []):
        if not isinstance(row, dict) or row.get("group") != "guardrail":
            continue
        values = row.get("values")
        bundle = values.get(variant_id) if isinstance(values, dict) else None
        score = number(bundle.get("score")) if isinstance(bundle, dict) else None
        if score is not None and score < min_score:
            failures.append({"metric": row.get("id"), "label": row.get("label"), "score": score})
    return failures


def schema_failures(data: dict[str, Any], variant_id: str) -> list[str]:
    failures = []
    for case in data.get("cases", []):
        if not isinstance(case, dict):
            continue
        for result in case.get("results", []):
            if not isinstance(result, dict) or str(result.get("variantId")) != variant_id:
                continue
            metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
            if result.get("parsedOk") is not True or metrics.get("schema_ok") is not True:
                failures.append(str(case.get("id") or result.get("caseId") or "case"))
    return failures


def make_review_url(data_path: Path, repo_root: Path) -> str | None:
    result = run_command(
        [sys.executable, str(SCRIPT_DIR / "make_review_url.py"), str(data_path), "--repo-root", str(repo_root)],
        cwd=repo_root,
        allow_failure=True,
    )
    if result.returncode:
        return None
    return result.stdout.strip() or None


def run_preflight(result: dict[str, Any], case_id: str, variant_id: str, provider_route: str, out_dir: Path, repo_root: Path) -> Path | None:
    prompt_path = result_artifact_prompt_path(result)
    if not prompt_path:
        return None
    out = out_dir / f"{slug(case_id)}__{slug(variant_id)}.json"
    run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "preflight_prompt_contract.py"),
            "--prompt",
            str(prompt_path),
            "--case-id",
            case_id,
            "--variant-id",
            variant_id,
            "--provider-route",
            provider_route,
            "--out",
            str(out),
        ],
        cwd=repo_root,
    )
    return out


def run_lab_variant(
    *,
    case: dict[str, Any],
    variant: dict[str, Any],
    round_dir: Path,
    config_dir: Path,
    provider: dict[str, Any],
    repo_root: Path,
    allow_fixture: bool,
) -> dict[str, Any]:
    case_path = Path(str(case["_source_path"]))
    system_path, user_path = variant_prompt_paths(variant, config_dir)
    surface = str(provider.get("surface") or provider.get("route") or "fixture")
    if surface == "fixture" and not allow_fixture:
        raise RuntimeError("fixture surface requires --allow-fixture because it cannot prove real A/B behavior")
    command = [
        sys.executable,
        str(SCRIPT_DIR / "lab_runner.py"),
        "--surface",
        surface,
        "--case",
        str(case_path),
        "--variant-id",
        str(variant["id"]),
        "--variant-label",
        str(variant.get("label") or variant["id"]),
        "--system",
        str(system_path),
        "--user",
        str(user_path),
        "--out-dir",
        str(round_dir / "artifacts" / "cases"),
        "--preset",
        str(provider.get("preset") or "pro-search"),
        "--max-output-tokens",
        str(int(provider.get("maxOutputTokens") or provider.get("max_output_tokens") or 1200)),
    ]
    if provider.get("envFile"):
        command.extend(["--env-file", str(resolve_path(str(provider["envFile"]), config_dir))])
    for domain in provider.get("domainFilter", []) if isinstance(provider.get("domainFilter"), list) else []:
        command.extend(["--domain-filter", str(domain)])
    expected_object = case.get("expectedObject") or provider.get("expectedObject")
    expected_host = case.get("expectedHost") or provider.get("expectedHost")
    if expected_object:
        command.extend(["--expected-object", str(expected_object)])
    if expected_host:
        command.extend(["--expected-host", str(expected_host)])
    fixture_response = variant.get("fixtureResponse") or case.get("fixtureResponse") or provider.get("fixtureResponse")
    if surface == "fixture":
        if not fixture_response:
            raise RuntimeError("fixture surface requires fixtureResponse on variant, case, or provider")
        command.extend(["--fixture-response", str(resolve_path(str(fixture_response), config_dir))])

    called_at = utc_now()
    result = run_command(command, cwd=repo_root, allow_failure=True)
    try:
        parsed = json_from_stdout(result, "lab_runner.py")
    except RuntimeError:
        return runner_failure_result(
            case=case,
            variant=variant,
            surface=surface,
            result=result,
            called_at=called_at,
        )
    parsed["provider_called_at"] = called_at
    parsed["runner_exit_code"] = result.returncode
    if result.stderr:
        parsed["runner_stderr"] = result.stderr
    return parsed


def build_round(
    *,
    config: dict[str, Any],
    config_path: Path,
    round_spec: dict[str, Any],
    round_index: int,
    completed_rounds: list[dict[str, Any]],
    repo_root: Path,
    allow_fixture: bool,
) -> dict[str, Any]:
    config_dir = config_path.parent
    campaign_dir = resolve_campaign_dir(str(config["campaignDir"]), config_dir, repo_root)
    round_id = str(round_spec.get("id") or f"round-{round_index:02d}-{slug(str(round_spec.get('lever') or 'candidate'))}")
    round_dir = campaign_dir / "03_rounds" / round_id
    artifacts_dir = round_dir / "artifacts"
    preflight_dir = artifacts_dir / "preflight"
    round_dir.mkdir(parents=True, exist_ok=True)

    baseline = dict(config.get("baseline") or {})
    candidate = dict(round_spec.get("candidate") or config.get("candidate") or {})
    if not baseline.get("id") or not candidate.get("id"):
        raise ValueError("config needs baseline.id and each round needs candidate.id")

    cases_dir = round_dir / "cases"
    cases = [normalize_case(item, cases_dir, config_dir) for item in (round_spec.get("cases") or config.get("cases") or [])]
    if not cases:
        raise ValueError("autonomous loop needs at least one case")

    provider = dict(config.get("provider") or {})
    provider_route = str(provider.get("route") or provider.get("surface") or "fixture")
    results: list[dict[str, Any]] = []
    preflight_paths: list[Path] = []
    for case in cases:
        case_id = str(case.get("id") or case.get("case_id") or "case")
        for variant in (baseline, candidate):
            result = run_lab_variant(
                case=case,
                variant=variant,
                round_dir=round_dir,
                config_dir=config_dir,
                provider=provider,
                repo_root=repo_root,
                allow_fixture=allow_fixture,
            )
            results.append(result)
            preflight_path = run_preflight(result, case_id, str(variant["id"]), provider_route, preflight_dir, repo_root)
            if preflight_path:
                preflight_paths.append(preflight_path)

    variants = [
        {
            "id": baseline["id"],
            "label": baseline.get("label") or baseline["id"],
            "name": baseline.get("label") or baseline["id"],
            "description": baseline.get("description") or "Baseline prompt or contract.",
        },
        {
            "id": candidate["id"],
            "label": candidate.get("label") or candidate["id"],
            "name": candidate.get("label") or candidate["id"],
            "description": candidate.get("description") or round_spec.get("lever") or "Candidate prompt or contract.",
        },
    ]
    summary = {
        "experiment": config.get("title") or "CE Prompt Improver autonomous A/B",
        "evidence_class": config.get("evidenceClass") or ("layout_smoke_not_ab_test" if provider_route == "fixture" else "live_local"),
        "source_prompt_contract": config.get("sourcePromptContract") or config.get("source"),
        "testset_source": config.get("testsetSource") or str(config_path),
        "variants": variants,
        "cases": [{key: value for key, value in case.items() if key != "_source_path"} for case in cases],
        "results": results,
        "not_proven": ["production_wiring", "deployment_readiness"],
        "test_intent": config.get("testIntent") or {},
        "test_design": config.get("testDesign") or {},
        "iteration_path": iteration_path_from_rounds(completed_rounds),
        "roundNavigation": build_round_navigation(completed_rounds, round_id),
    }
    raw_summary_path = artifacts_dir / "results-summary.raw.json"
    normalized_summary_path = artifacts_dir / "results-summary.json"
    data_path = round_dir / "html" / "assets" / "data.json"
    write_json(raw_summary_path, summary)
    run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "normalize_results_summary_from_artifacts.py"),
            "--results",
            str(raw_summary_path),
            "--out",
            str(normalized_summary_path),
        ],
        cwd=repo_root,
    )
    build_command = [
        sys.executable,
        str(SCRIPT_DIR / "build_review_surface_data.py"),
        "--results",
        str(normalized_summary_path),
        "--out",
        str(data_path),
    ]
    for preflight_path in preflight_paths:
        build_command.extend(["--preflight", str(preflight_path)])
    run_command(build_command, cwd=repo_root)
    trace_report_path = artifacts_dir / "trace-integrity-report.json"
    validation_path = artifacts_dir / "review-data-validation.json"
    real_validation_path = artifacts_dir / "review-data-real-ab-validation.json"
    trace_result = run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "verify_review_surface_trace.py"),
            "--results",
            str(normalized_summary_path),
            "--data",
            str(data_path),
            "--out",
            str(trace_report_path),
        ],
        cwd=repo_root,
        allow_failure=True,
    )
    validation_result = run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_review_data.py"),
            str(data_path),
            "--out",
            str(validation_path),
        ],
        cwd=repo_root,
        allow_failure=True,
    )
    real_validation = run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_review_data.py"),
            str(data_path),
            "--require-real-ab",
            "--out",
            str(real_validation_path),
        ],
        cwd=repo_root,
        allow_failure=True,
    )

    data = load_json(data_path)
    trace_report = load_report_or_failure(trace_report_path, "trace_integrity", trace_result)
    validation = load_report_or_failure(validation_path, "review_data_validation", validation_result)
    real_report = load_report_or_failure(real_validation_path, "real_ab_validation", real_validation)
    promotion = dict(config.get("promotion") or {})
    candidate_id = str(candidate["id"])
    baseline_id = str(baseline["id"])
    candidate_score = metric_average(data, candidate_id, {"primary", "guardrail"})
    baseline_score = metric_average(data, baseline_id, {"primary", "guardrail"})
    min_score = float(promotion.get("minCandidateScore") or 4.2)
    min_delta = float(promotion.get("minDelta") or 0.0)
    min_guardrail = float(promotion.get("minGuardrailScore") or 4.0)
    real_ab_policy = config_gate_policy(promotion.get("requireRealAb"), default=True, field="requireRealAb")
    schema_policy = config_gate_policy(promotion.get("requireSchemaOk"), default=True, field="requireSchemaOk")
    trace_policy = config_gate_policy(promotion.get("requireTraceIntegrity"), default=True, field="requireTraceIntegrity")
    failures: list[dict[str, Any]] = []
    if validation.get("status") != "pass":
        failures.append({"gate": "review_data_validation", "status": validation.get("status"), "issues": validation.get("issues")})
    if real_ab_policy in NON_PASSING_GATE_POLICIES:
        failures.append(non_passing_gate("real_ab_validation", real_ab_policy))
    elif real_ab_policy == "required" and real_report.get("status") != "pass":
        failures.append({"gate": "real_ab_validation", "status": real_report.get("status"), "issues": real_report.get("issues")})
    if trace_policy in NON_PASSING_GATE_POLICIES:
        failures.append(non_passing_gate("trace_integrity", trace_policy))
    elif trace_policy == "required" and trace_report.get("status") != "pass":
        failures.append({"gate": "trace_integrity", "status": trace_report.get("status"), "issues": trace_report.get("issues")})
    guardrail_issues = guardrail_failures(data, candidate_id, min_guardrail)
    if guardrail_issues:
        failures.append({"gate": "candidate_guardrails", "issues": guardrail_issues})
    schema_issues = schema_failures(data, candidate_id) if schema_policy == "required" else []
    if schema_policy in NON_PASSING_GATE_POLICIES:
        failures.append(non_passing_gate("candidate_schema", schema_policy))
    elif schema_issues:
        failures.append({"gate": "candidate_schema", "caseIds": schema_issues})
    if candidate_score is None or candidate_score < min_score:
        failures.append({"gate": "candidate_score", "score": candidate_score, "min": min_score})
    if candidate_score is not None and baseline_score is not None and candidate_score < baseline_score + min_delta:
        failures.append({"gate": "candidate_delta", "candidateScore": candidate_score, "baselineScore": baseline_score, "minDelta": min_delta})

    accepted = not failures
    return {
        "id": round_id,
        "label": round_spec.get("label") or f"R{round_index:02d} {round_spec.get('lever') or candidate_id}",
        "lever": round_spec.get("lever") or candidate.get("description") or candidate_id,
        "roundDir": str(round_dir),
        "dataPath": str(data_path),
        "reviewUrl": make_review_url(data_path, repo_root),
        "resultsSummary": str(normalized_summary_path),
        "traceReport": str(trace_report_path),
        "validationReport": str(validation_path),
        "realAbValidationReport": str(real_validation_path),
        "candidateId": candidate_id,
        "baselineId": baseline_id,
        "candidateScore": round(candidate_score, 3) if candidate_score is not None else None,
        "baselineScore": round(baseline_score, 3) if baseline_score is not None else None,
        "accepted": accepted,
        "failedGates": failures,
        "summary": "Candidate passed autonomous gates." if accepted else "Candidate did not pass autonomous gates.",
        "stopReason": "accepted_candidate" if accepted else "continue_or_budget_exhausted",
        "realAbValidatorExitCode": real_validation.returncode,
    }


def rebuild_with_final_navigation(state: dict[str, Any], repo_root: Path) -> None:
    rounds = state.get("rounds")
    if not isinstance(rounds, list):
        return
    iteration_path = iteration_path_from_rounds(rounds)
    for item in rounds:
        if not isinstance(item, dict):
            continue
        summary_path = Path(str(item.get("resultsSummary") or ""))
        data_path = Path(str(item.get("dataPath") or ""))
        if not summary_path.exists() or not data_path:
            continue
        summary = load_json(summary_path)
        if not isinstance(summary, dict):
            continue
        summary["iteration_path"] = iteration_path
        summary["roundNavigation"] = build_round_navigation(rounds, str(item.get("id") or ""))
        write_json(summary_path, summary)
        preflight_paths = sorted((Path(str(item["roundDir"])) / "artifacts" / "preflight").glob("*.json"))
        build_command = [
            sys.executable,
            str(SCRIPT_DIR / "build_review_surface_data.py"),
            "--results",
            str(summary_path),
            "--out",
            str(data_path),
        ]
        for preflight_path in preflight_paths:
            build_command.extend(["--preflight", str(preflight_path)])
        run_command(build_command, cwd=repo_root)


def write_decision_packet(config: dict[str, Any], state: dict[str, Any], campaign_dir: Path) -> Path:
    status = str(state.get("status") or "inconclusive")
    accepted = state.get("acceptedRound") if isinstance(state.get("acceptedRound"), dict) else None
    packet_path = campaign_dir / "05_promotion-packets" / f"{utc_now().replace(':', '-').replace('Z', '')}__{status}.md"
    failed_gates = state.get("failedGates") if isinstance(state.get("failedGates"), list) else []
    accepted_delta = (
        f"Accepted candidate `{accepted.get('candidateId')}` from `{accepted.get('id')}`."
        if accepted
        else "No candidate accepted. See failed gates and review URL."
    )
    lines = [
        "# Prompt promotion packet",
        "",
        f"Status: `{status}`",
        "",
        "## Accepted delta",
        "",
        accepted_delta,
        "",
        "## Source status labels",
        "",
        f"- Goal source: `{config.get('source') or 'not_supplied'}`",
        "- Lab evidence: `current_runtime_evidence` for provider/replay artifacts; production wiring remains `not_claimed`.",
        "",
        "## Must-survive facts",
        "",
    ]
    must_survive = config.get("mustSurvive") if isinstance(config.get("mustSurvive"), list) else []
    lines.extend([f"- {item}" for item in must_survive] or ["- Not supplied in loop config."])
    lines.extend(["", "## Must-reject behaviors", ""])
    must_reject = config.get("mustReject") if isinstance(config.get("mustReject"), list) else []
    lines.extend([f"- {item}" for item in must_reject] or ["- Not supplied in loop config."])
    lines.extend(
        [
            "",
            "## Evidence gathered",
            "",
            f"- Rounds executed: {len(state.get('rounds') or [])}",
            f"- Final review URL: {state.get('latestReviewUrl') or 'not_available'}",
            f"- Autonomous state: `{campaign_dir / 'autonomous-run-state.json'}`",
            "",
            "## What this proves",
            "",
            "- The lab runner executed the configured cases and variants and built a PromptReview-compatible evidence packet.",
            "- Passing candidates satisfy only the configured lab gates, not production wiring.",
            "",
            "## What this does not prove",
            "",
            "- Production prompt files, runtime parsers, dashboard consumers, deployment, or customer API readiness.",
            "",
            "## Failed gates",
            "",
        ]
    )
    if failed_gates:
        lines.append("```json")
        lines.append(json.dumps(failed_gates, ensure_ascii=False, indent=2))
        lines.append("```")
    else:
        lines.append("- None recorded.")
    lines.extend(["", "## Recommended CE next step", ""])
    lines.append("Run `ce-plan` or `ce-work` with this promotion packet before production wiring." if accepted else "Revise candidate levers or add cases, then rerun `ce-prompt-improver`.")
    write_text(packet_path, "\n".join(lines) + "\n")
    return packet_path


def run_loop(config_path: Path, repo_root: Path, allow_fixture: bool, max_rounds_override: int | None) -> dict[str, Any]:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise ValueError("loop config must be a JSON object")
    if "campaignDir" not in config:
        raise ValueError("loop config requires campaignDir")
    campaign_dir = resolve_campaign_dir(str(config["campaignDir"]), config_path.parent, repo_root)
    campaign_dir.mkdir(parents=True, exist_ok=True)
    rounds_config = config.get("rounds")
    if not isinstance(rounds_config, list) or not rounds_config:
        rounds_config = [{"id": "round-01-candidate", "candidate": config.get("candidate") or {}, "lever": "candidate"}]
    budget = dict(config.get("budget") or {})
    max_rounds = max_rounds_override or int(budget.get("maxRounds") or len(rounds_config))
    state: dict[str, Any] = {
        "status": "running",
        "mode": config.get("mode") or "autonomous_candidate_search",
        "startedAt": utc_now(),
        "updatedAt": utc_now(),
        "configPath": str(config_path),
        "campaignDir": str(campaign_dir),
        "budget": {"maxRounds": max_rounds, "configuredRounds": len(rounds_config)},
        "rounds": [],
        "failedGates": [],
    }
    write_json(campaign_dir / "autonomous-run-state.json", state)

    try:
        validate_promotion_config(dict(config.get("promotion") or {}))
        for index, round_spec in enumerate(rounds_config[:max_rounds], start=1):
            completed_rounds = list(state["rounds"]) + [
                {
                    "id": str(round_spec.get("id") or f"round-{index:02d}"),
                    "label": round_spec.get("label") or f"R{index:02d}",
                    "lever": round_spec.get("lever") or "candidate",
                }
            ]
            round_result = build_round(
                config=config,
                config_path=config_path,
                round_spec=round_spec,
                round_index=index,
                completed_rounds=completed_rounds,
                repo_root=repo_root,
                allow_fixture=allow_fixture,
            )
            state["rounds"].append(round_result)
            state["latestReviewUrl"] = round_result.get("reviewUrl")
            state["updatedAt"] = utc_now()
            write_json(campaign_dir / "autonomous-run-state.json", state)
            if round_result["accepted"]:
                state["status"] = "accepted_candidate"
                state["acceptedRound"] = round_result
                state["stopReason"] = "promotion_threshold_met"
                break
    except Exception as exc:  # noqa: BLE001
        state["status"] = "failed"
        state["stopReason"] = "runner_exception"
        state["error"] = str(exc)
        state["failedGates"] = [
            {
                "gate": "runner_exception",
                "status": "failed",
                "issues": [{"message": str(exc)}],
            }
        ]
        state["updatedAt"] = utc_now()
        try:
            packet_path = write_decision_packet(config, state, campaign_dir)
            state["decisionPacket"] = str(packet_path)
        except Exception as packet_exc:  # noqa: BLE001
            state["decisionPacketError"] = str(packet_exc)
        write_json(campaign_dir / "autonomous-run-state.json", state)
        return state

    if state.get("status") == "running":
        state["status"] = "inconclusive"
        state["stopReason"] = "budget_exhausted" if len(state["rounds"]) >= max_rounds else "no_rounds_left"
        if state["rounds"]:
            state["failedGates"] = state["rounds"][-1].get("failedGates") or []
    rebuild_with_final_navigation(state, repo_root)
    packet_path = write_decision_packet(config, state, campaign_dir)
    state["decisionPacket"] = str(packet_path)
    state["updatedAt"] = utc_now()
    write_json(campaign_dir / "autonomous-run-state.json", state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Run autonomous CE Prompt Improver A/B rounds from a manifest.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--allow-fixture", action="store_true", help="Allow fixture runs for script/layout smoke tests. They cannot pass real A/B gates by default.")
    parser.add_argument("--max-rounds", type=int)
    args = parser.parse_args()

    state = run_loop(args.config.resolve(), args.repo_root.resolve(), args.allow_fixture, args.max_rounds)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    if state.get("status") == "accepted_candidate":
        return 0
    if state.get("status") == "failed":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
