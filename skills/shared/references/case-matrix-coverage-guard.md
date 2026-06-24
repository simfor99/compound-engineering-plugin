# CE case matrix coverage guard

Use this reference when a CE workflow plans, reviews, implements, or reports
work whose behavior is defined by a set of cases, states, branches, personas,
edge cases, fixtures, acceptance examples, or decision outcomes.

This guard is mandatory when any case outcome depends on an LLM/provider call,
scraper, browser journey, auth/session gate, workflow start/completion,
persistence, trace visibility, external side effect, or production-readiness
claim.

## Core rule

A representative smoke test does not close a case matrix.

If a requirements or plan artifact names a case matrix, UX matrix, acceptance
example set, state machine, or decision matrix, every row that supports a
readiness claim needs a mapped verification scenario. "At least one `pass`, one
warning, and one blocker" is a smoke gate, not readiness, unless the origin
matrix itself has only those three rows.

## Required fields

For each readiness-bearing case, record:

```text
Case ID: <stable id from the requirements, plan, or test matrix>
Input / setup: <the concrete condition being exercised>
Expected user-visible outcome: <copy/action/state the user sees>
Expected machine outcome: <state, API result, persistence, workflow effect>
Evidence class: static_mock|artifact_replay|unit_mocked|integration_local|live_local|production_like|manual_user_verified
Claim class: ui_rendering|browser_interaction|api_contract|workflow_start|workflow_completion|provider_behavior|prompt_fidelity|persistence|trace_visibility|side_effect_delivery|production_readiness
Readiness gate: required|smoke_only|deferred|not_applicable
Proves: <narrow claim directly proven>
Does not prove: <stronger claim still open>
```

Use the evidence and claim classes from `evidence-authenticity-guard.md` and
`evidence-claim-integrity-guard.md`.

## Planning rules

- Brainstorm outputs should include a case matrix when the discussion discovers
  more than three meaningful product states, edge cases, or acceptance
  examples, or when the user explicitly asks to test cases.
- Plans must map every origin case that affects readiness to at least one
  implementation-unit test scenario or explicit quality gate.
- If the first planned pass uses mocks, replay, static data, or a prototype,
  add a separate live follow-up gate before any runtime, scraper, provider,
  workflow, auth, persistence, side-effect, or production-readiness claim.
- If live testing is too expensive or unsafe for the current scope, mark the
  corresponding readiness gate `deferred` or `not_claimed`. Do not silently
  replace it with a weaker proof.

## Execution rules

Before claiming a task, feature, or plan complete:

1. List the origin cases that the claim covers.
2. Mark each as `passed`, `failed`, `blocked`, `deferred`, `not_claimed`, or
   `not_applicable`.
3. For every `passed` case, cite evidence with the actual evidence class.
4. For every `failed` case, fix or narrow the claim.
5. For every `blocked`, `deferred`, or `not_claimed` case, state what claim is
   intentionally not being made.

Do not claim that a decision matrix is "tested", "green", "ready", or
"production-ready" while any readiness-required row remains unverified.

## Review behavior

Document review, code review, dogfood, and shipping workflows should flag a
missing case-to-test mapping when:

- an origin matrix exists but the plan tests only representative examples;
- LLM/provider/scraper/workflow behavior is claimed from replay, mock, or UI
  projection only;
- a start/ship/readiness gate lacks explicit coverage for blocker and recovery
  cases;
- the document says "all cases", "matrix", "readiness", or "production" but
  does not identify which rows passed and which remain deferred.

## Reporting receipt

For material case-matrix claims, include:

```text
Matrix: <name or source path>
Rows in scope: <n>
Passed: <ids>
Failed: <ids or none>
Blocked/deferred/not claimed: <ids or none>
Evidence classes used: <summary>
Readiness claim allowed: yes|no|limited_to_smoke
Residual risk: <remaining gap or not_applicable>
```
