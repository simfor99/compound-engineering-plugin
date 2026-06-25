#!/usr/bin/env python3
"""Self-test for CE Prompt Improver helper scripts."""

from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)


def main() -> int:
    repo_root = Path.cwd()
    loop_spec = importlib.util.spec_from_file_location(
        "autonomous_prompt_loop",
        SKILL_DIR / "scripts" / "autonomous_prompt_loop.py",
    )
    assert loop_spec and loop_spec.loader
    loop_module = importlib.util.module_from_spec(loop_spec)
    loop_spec.loader.exec_module(loop_module)
    assert loop_module.config_bool("false", default=True, field="requireRealAb") is False
    assert loop_module.config_bool("true", default=False, field="requireRealAb") is True

    with tempfile.TemporaryDirectory(prefix="ce-prompt-improver-self-test-") as raw_tmp:
        tmp = Path(raw_tmp)
        round_results = tmp / "round-results.json"
        shutil.copyfile(SKILL_DIR / "templates" / "round-results.template.json", round_results)
        data_path = tmp / "html" / "assets" / "data.json"

        run([
            sys.executable,
            str(SKILL_DIR / "scripts" / "build_review_data.py"),
            "--round-results",
            str(round_results),
            "--out",
            str(data_path),
        ], repo_root)
        validation = run([
            sys.executable,
            str(SKILL_DIR / "scripts" / "validate_review_data.py"),
            str(data_path),
        ], repo_root)
        validation_report = json.loads(validation.stdout)
        assert validation_report["status"] == "pass", validation.stdout

        scaffold_root = tmp / "scaffold"
        scaffold = run([
            sys.executable,
            str(SKILL_DIR / "scripts" / "scaffold_lab.py"),
            "--slug",
            "guard-smoke",
            "--source",
            "docs/brainstorms/example.md",
            "--workspace-root",
            str(scaffold_root),
            "--timestamp",
            "fixed",
        ], repo_root)
        assert "fallback workspace is not docs/todo" in scaffold.stdout, scaffold.stdout
        state_path = scaffold_root / "guard-smoke" / "fixed" / "campaign-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["workspace_reason"] == "fallback_non_render_workspace", state

        loop_root = tmp / "autonomous"
        prompt_dir = loop_root / "prompts"
        prompt_dir.mkdir(parents=True)
        system_a = prompt_dir / "system-a.txt"
        user_a = prompt_dir / "user-a.txt"
        system_b = prompt_dir / "system-b.txt"
        user_b = prompt_dir / "user-b.txt"
        fixture = prompt_dir / "fixture-response.json"
        system_a.write_text("Return JSON for $companyName.", encoding="utf-8")
        user_a.write_text("URL: $submitted_url", encoding="utf-8")
        system_b.write_text("Return JSON with dashboard_page_context for $companyName.", encoding="utf-8")
        user_b.write_text("URL: $submitted_url", encoding="utf-8")
        fixture.write_text(
            json.dumps(
                {
                    "dashboard_page_context": {
                        "page_role_summary": "specific_offering_page",
                        "market_language_summary": "fits",
                        "customer_safe_context_note": "We read this as a specific offering page.",
                        "visible_basis": ["Service page"],
                    },
                    "source_refs": [{"url": "https://example.com"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        loop_config = loop_root / "autonomous-loop-config.json"
        loop_config.write_text(
            json.dumps(
                {
                    "mode": "autonomous_candidate_search",
                    "title": "Autonomous fixture smoke",
                    "campaignDir": str(loop_root / "campaign"),
                    "provider": {
                        "surface": "fixture",
                        "route": "fixture",
                        "fixtureResponse": str(fixture),
                    },
                    "budget": {"maxRounds": 2},
                    "promotion": {"requireRealAb": True, "minCandidateScore": 0, "minGuardrailScore": 0},
                    "baseline": {
                        "id": "A_current",
                        "label": "A Current",
                        "system": str(system_a),
                        "user": str(user_a),
                    },
                    "rounds": [
                        {
                            "id": "round-01-fixture-smoke",
                            "label": "R01 Fixture Smoke",
                            "lever": "Fixture smoke must not promote",
                            "candidate": {
                                "id": "B_candidate",
                                "label": "B Candidate",
                                "system": str(system_b),
                                "user": str(user_b),
                            },
                            "cases": [
                                {
                                    "id": "case-01",
                                    "companyName": "Example",
                                    "submitted_url": "https://example.com/service",
                                    "expectedObject": "dashboard_page_context",
                                }
                            ],
                        },
                        {
                            "id": "round-02-fixture-smoke",
                            "label": "R02 Fixture Smoke",
                            "lever": "Second fixture smoke keeps navigation",
                            "candidate": {
                                "id": "B_candidate",
                                "label": "B Candidate",
                                "system": str(system_b),
                                "user": str(user_b),
                            },
                            "cases": [
                                {
                                    "id": "case-01",
                                    "companyName": "Example",
                                    "submitted_url": "https://example.com/service",
                                    "expectedObject": "dashboard_page_context",
                                }
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        loop = subprocess.run(
            [
                sys.executable,
                str(SKILL_DIR / "scripts" / "autonomous_prompt_loop.py"),
                "--config",
                str(loop_config),
                "--allow-fixture",
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        assert loop.returncode == 2, loop.stdout + loop.stderr
        loop_state = json.loads(loop.stdout)
        assert loop_state["status"] == "inconclusive", loop_state
        assert len(loop_state["rounds"]) == 2, loop_state
        round_data = Path(loop_state["rounds"][0]["dataPath"])
        assert round_data.exists(), loop_state
        report_data = json.loads(round_data.read_text(encoding="utf-8"))
        assert len(report_data["roundNavigation"]) == 2, report_data.get("roundNavigation")
        assert report_data["roundNavigation"][0]["current"] is True, report_data.get("roundNavigation")
        assert report_data["roundNavigation"][1]["href"], report_data.get("roundNavigation")
        assert loop_state["decisionPacket"], loop_state

        fake_repo = tmp / "fake-repo"
        relative_campaign = Path("docs/todo/2026_06_04/07_experiments/repo-relative-runner-failure")
        intake_dir = fake_repo / relative_campaign / "01_intake"
        intake_dir.mkdir(parents=True)
        failure_config = intake_dir / "autonomous-loop-config.json"
        failure_config.write_text(
            json.dumps(
                {
                    "mode": "autonomous_candidate_search",
                    "title": "Repo-relative runner failure smoke",
                    "campaignDir": str(relative_campaign),
                    "provider": {
                        "surface": "not-a-real-surface",
                        "route": "not-a-real-surface",
                    },
                    "budget": {"maxRounds": 1},
                    "promotion": {
                        "requireRealAb": "false",
                        "requireTraceIntegrity": "true",
                        "requireSchemaOk": "true",
                        "minCandidateScore": 0,
                        "minGuardrailScore": 0,
                    },
                    "baseline": {
                        "id": "A_current",
                        "label": "A Current",
                        "system": str(system_a),
                        "user": str(user_a),
                    },
                    "rounds": [
                        {
                            "id": "round-01-runner-failure",
                            "label": "R01 Runner Failure",
                            "lever": "Runner failure must produce state",
                            "candidate": {
                                "id": "B_candidate",
                                "label": "B Candidate",
                                "system": str(system_b),
                                "user": str(user_b),
                            },
                            "cases": [
                                {
                                    "id": "case-01",
                                    "companyName": "Example",
                                    "submitted_url": "https://example.com/service",
                                    "expectedObject": "dashboard_page_context",
                                }
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        failure_loop = subprocess.run(
            [
                sys.executable,
                str(SKILL_DIR / "scripts" / "autonomous_prompt_loop.py"),
                "--config",
                str(failure_config),
                "--repo-root",
                str(fake_repo),
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        assert failure_loop.returncode == 2, failure_loop.stdout + failure_loop.stderr
        failure_state = json.loads(failure_loop.stdout)
        expected_campaign = fake_repo / relative_campaign
        assert Path(failure_state["campaignDir"]) == expected_campaign, failure_state
        assert failure_state["status"] == "inconclusive", failure_state
        assert Path(failure_state["decisionPacket"]).exists(), failure_state
        assert failure_state["failedGates"], failure_state
        failure_packet = Path(failure_state["decisionPacket"]).read_text(encoding="utf-8")
        assert "candidate_schema" in failure_packet or "trace_integrity" in failure_packet, failure_packet
        failure_summary = json.loads(Path(failure_state["rounds"][0]["resultsSummary"]).read_text(encoding="utf-8"))
        failure_results = failure_summary.get("results") or []
        assert failure_results and all(item.get("runner_exit_code") for item in failure_results), failure_results
        assert all((item.get("metrics") or {}).get("provider_error") for item in failure_results), failure_results

        provider_error_dir = fake_repo / "docs/todo/2026_06_04/07_experiments/provider-error-json/01_intake"
        provider_error_dir.mkdir(parents=True)
        provider_error_config = provider_error_dir / "autonomous-loop-config.json"
        provider_error_payload = json.loads(failure_config.read_text(encoding="utf-8"))
        provider_error_payload["title"] = "Provider JSON error should stay diagnostic"
        provider_error_payload["campaignDir"] = "docs/todo/2026_06_04/07_experiments/provider-error-json"
        provider_error_payload["provider"] = {
            "surface": "perplexity-agent",
            "route": "perplexity-agent",
        }
        provider_error_payload["promotion"] = {
            "requireRealAb": "false",
            "requireTraceIntegrity": "true",
            "requireSchemaOk": "true",
            "minCandidateScore": 0,
            "minGuardrailScore": 0,
        }
        provider_error_config.write_text(json.dumps(provider_error_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        provider_env = dict(os.environ)
        provider_env.pop("PERPLEXITY_API_KEY", None)
        provider_env.pop("VITE_PERPLEXITY_API_KEY", None)
        provider_error_loop = subprocess.run(
            [
                sys.executable,
                str(SKILL_DIR / "scripts" / "autonomous_prompt_loop.py"),
                "--config",
                str(provider_error_config),
                "--repo-root",
                str(fake_repo),
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            env=provider_env,
        )
        assert provider_error_loop.returncode == 2, provider_error_loop.stdout + provider_error_loop.stderr
        provider_error_state = json.loads(provider_error_loop.stdout)
        provider_error_summary = json.loads(Path(provider_error_state["rounds"][0]["resultsSummary"]).read_text(encoding="utf-8"))
        provider_error_results = provider_error_summary.get("results") or []
        assert provider_error_results and all(item.get("runner_exit_code") == 1 for item in provider_error_results), provider_error_results
        assert all((item.get("metrics") or {}).get("provider_error") for item in provider_error_results), provider_error_results

        not_claimed_dir = fake_repo / "docs/todo/2026_06_04/07_experiments/not-claimed-gate/01_intake"
        not_claimed_dir.mkdir(parents=True)
        not_claimed_config = not_claimed_dir / "autonomous-loop-config.json"
        not_claimed_payload = json.loads(failure_config.read_text(encoding="utf-8"))
        not_claimed_payload["title"] = "Not-claimed gate should not crash"
        not_claimed_payload["campaignDir"] = "docs/todo/2026_06_04/07_experiments/not-claimed-gate"
        not_claimed_payload["provider"] = {
            "surface": "fixture",
            "route": "fixture",
            "fixtureResponse": str(fixture),
        }
        not_claimed_payload["promotion"] = {
            "requireRealAb": "not_claimed",
            "requireTraceIntegrity": "false",
            "requireSchemaOk": "false",
            "minCandidateScore": 0,
            "minGuardrailScore": 0,
        }
        not_claimed_config.write_text(json.dumps(not_claimed_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        not_claimed_loop = subprocess.run(
            [
                sys.executable,
                str(SKILL_DIR / "scripts" / "autonomous_prompt_loop.py"),
                "--config",
                str(not_claimed_config),
                "--repo-root",
                str(fake_repo),
                "--allow-fixture",
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        assert not_claimed_loop.returncode == 2, not_claimed_loop.stdout + not_claimed_loop.stderr
        not_claimed_state = json.loads(not_claimed_loop.stdout)
        assert not_claimed_state["status"] == "inconclusive", not_claimed_state
        assert not_claimed_state["failedGates"][0]["status"] == "not_claimed", not_claimed_state

        crash_dir = fake_repo / "docs/todo/2026_06_04/07_experiments/crash-state/01_intake"
        crash_dir.mkdir(parents=True)
        crash_config = crash_dir / "autonomous-loop-config.json"
        crash_payload = json.loads(failure_config.read_text(encoding="utf-8"))
        crash_payload["title"] = "Crash state must finalize"
        crash_payload["campaignDir"] = "docs/todo/2026_06_04/07_experiments/crash-state"
        crash_payload["provider"] = {"surface": "fixture", "route": "fixture", "fixtureResponse": str(fixture)}
        crash_payload["promotion"] = {"requireRealAb": "false", "requireTraceIntegrity": "false", "requireSchemaOk": "false"}
        crash_payload["baseline"].pop("id", None)
        crash_config.write_text(json.dumps(crash_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        crash_loop = subprocess.run(
            [
                sys.executable,
                str(SKILL_DIR / "scripts" / "autonomous_prompt_loop.py"),
                "--config",
                str(crash_config),
                "--repo-root",
                str(fake_repo),
                "--allow-fixture",
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        assert crash_loop.returncode == 1, crash_loop.stdout + crash_loop.stderr
        crash_state = json.loads(crash_loop.stdout)
        assert crash_state["status"] == "failed", crash_state
        assert crash_state["stopReason"] == "runner_exception", crash_state
        persisted_crash_state = json.loads((fake_repo / "docs/todo/2026_06_04/07_experiments/crash-state/autonomous-run-state.json").read_text(encoding="utf-8"))
        assert persisted_crash_state["status"] == "failed", persisted_crash_state

    print(json.dumps({"status": "pass", "skill_dir": str(SKILL_DIR)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
