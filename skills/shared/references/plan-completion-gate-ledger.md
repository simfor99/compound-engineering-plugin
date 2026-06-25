# Plan Completion Gate Ledger

Use this guard when `ce-work` executes from a plan document. Its job is to stop
the common failure mode where a convincing partial proof feels like feature
completion.

## When this guard applies

Apply this guard for every plan-file input (`.md` or `.html`) and for bare
prompts that the agent turns into an explicit task plan with acceptance gates.
It is mandatory when the work mentions readiness, workflow starts, browser
testing, persistence, provider calls, traces, production evidence, UI states,
case matrices, or "done" claims.

## Build the ledger before execution

Before implementation starts, extract a completion ledger from the plan. Use
the plan's own terms and IDs when available.

Rows come from:

- Requirements, acceptance criteria, or requirement trace sections.
- Implementation Units, Work Breakdown, or task sections.
- Verification, Test Scenarios, Evidence, Browser, Persistence, or Rollout
  sections.
- Case matrices, UX matrices, state machines, decision tables, or examples.
- Scope Boundaries and explicit non-goals.
- Deferred to Implementation, Implementation-Time Unknowns, or open questions.

Minimum columns:

| Plan item | Required proof | Evidence produced | Status | Claim allowed | Residual action |
|---|---|---|---|---|---|

Use stable IDs from the plan. If the plan has no IDs, use short section labels
instead of inventing permanent IDs.

## Status vocabulary

- `passed`: the required proof exists and matches the same runtime, target,
  surface, environment, or data store named by the plan.
- `failed`: evidence exists and contradicts the required behavior.
- `blocked`: proof cannot be produced without missing credentials, service
  access, user input, external state, or a broken prerequisite.
- `deferred`: the plan or Simon explicitly accepted postponing this gate.
- `not_claimed`: the implementation may exist, but the required evidence was
  not produced and no readiness claim is allowed.
- `not_applicable`: the row does not apply after implementation, with a short
  reason.

Do not use `passed` for smoke-only evidence unless the plan only required a
smoke check. Do not use `passed` for mocked, replay, fixture, static, or
request-intercepted evidence when the plan required live runtime, live backend,
provider, scraper, auth, workflow, Supabase, persistence, trace visibility, or
production/staging behavior.

## Completion rule

Before final summary, compare the intended completion claim with the ledger:

- All required rows `passed` -> `verified_complete` may be claimed.
- Any required row `deferred` or `not_claimed` -> at most
  `verified_with_deferrals`; name the rows.
- Any required row `failed` -> `not_complete`; fix it or report failure.
- Any required row `blocked` -> `blocked`; name the blocker and the smallest
  next action.

The final answer must not be stronger than the weakest required ledger row.
Green unit tests, a clean typecheck, a positive code review, or a single happy
path browser run cannot override open ledger rows.

## Evidence receipt

If the repo has a plan-local evidence receipt, update it before final summary:

- Preferred sidecar for `docs/plans/<plan>.md`:
  `docs/plans/<plan-stem>/evidence-receipt.md`
- If no sidecar exists and the change is small, include the ledger in the final
  answer.
- Do not edit the plan body as progress state. The plan remains the decision
  artifact; the ledger records execution evidence.

The receipt should include:

- The ledger table or a compact matrix.
- Commands, artifacts, screenshots, run IDs, trace paths, or readback paths.
- `proves` and `does_not_prove` for broad claims.
- Remaining gates and whether they are `blocked`, `deferred`, or
  `not_claimed`.

## Final answer checklist

Before saying "done", answer these internally:

1. Did I map every plan verification gate, not only the gates I happened to
   test?
2. Did I classify each evidence item by strength and runtime class?
3. Did I downgrade the final claim for every open row?
4. Did I tell Simon the next manual test link or command only after the live
   path class was actually probed?
5. Did I avoid turning a partial proof into a completion claim?
