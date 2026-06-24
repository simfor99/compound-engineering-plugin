# CE evidence claim integrity guard

Use this reference with `evidence-authenticity-guard.md` whenever tests,
browser checks, API calls, traces, workflows, provider calls, or review
surfaces are used to support a readiness or completion claim.

## Core rule

Evidence only proves the exact claim it directly exercises.

A browser observation does not automatically prove backend persistence. An
HTTP 200 does not automatically prove downstream workflow completion. A trace
file does not automatically prove the trace is indexed, reloadable, or visible
in the admin surface. A unit test with mocks does not prove integration.

## Claim classes

Use the narrowest honest claim class:

| Claim class | Evidence normally required |
|---|---|
| `ui_rendering` | Browser/screenshot/accessibility evidence for the visible state. |
| `browser_interaction` | Browser action plus observed state/network behavior. |
| `api_contract` | Real request/response shape through the target endpoint. |
| `workflow_start` | Accepted entry request plus durable run/workflow identifier. |
| `workflow_completion` | Downstream terminal state and expected artifacts. |
| `provider_behavior` | Real configured provider call, request capture, and output. |
| `prompt_fidelity` | Source contract, rendered prompt, effective provider request, and output validation as applicable. |
| `persistence` | Same-target write-read evidence against the claimed environment. |
| `trace_visibility` | Trace generation plus reload/index/admin or consumer visibility. |
| `side_effect_delivery` | Delivery/readback from the external system or accepted sandbox equivalent. |
| `production_readiness` | Production-like entry, auth, persistence, observability, rollback/cleanup stance, and relevant failure paths. |

## Required receipt

For material readiness or completion claims, include:

```text
Claim: <claim_class>: <specific subject>
Evidence class: static_mock|artifact_replay|unit_mocked|integration_local|live_local|production_like|manual_user_verified
Evidence: <paths, commands, traces, screenshots, logs, provider run IDs, or database proof>
Proves: <narrow claim actually proven>
Does not prove: <stronger claims a reader might infer incorrectly>
Residual risk: <remaining gap or not_applicable>
```

## Blocking rules

- Do not claim `workflow_completion` from `workflow_start`.
- Do not claim `persistence` from UI, API, trace, migration, or generated-type
  evidence without same-target readback.
- Do not claim `provider_behavior` from rendered prompt, parser tests, fixture
  outputs, or replay.
- Do not claim `trace_visibility` from trace-file creation alone.
- Do not claim `production_readiness` from local live evidence unless the
  missing production-like legs are explicitly listed as unproven.

## Review behavior

`ce-plan`, `ce-work`, `ce-code-review`, `ce-doc-review`, `ce-dogfood-beta`, and
`lfg` must flag oversized claims as findings or residual risk. A correct report
may say `not_claimed`; it must not silently upgrade weak evidence.
