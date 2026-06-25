# Evidence authenticity guard

This reference is the single source of truth for Compound Engineering test,
prototype, browser, and readiness evidence claims. Apply it whenever a skill
plans, executes, reviews, dogfoods, or reports tests for behavior that could be
fixture-backed, replay-backed, mocked, simulated, live, or production-like.

When the result supports a material readiness or completion claim, also apply
`./evidence-claim-integrity-guard.md`. Evidence class answers "what kind of
test ran"; claim integrity answers "what exact statement that evidence proves."
When the claim depends on email, billing, webhooks, queues, trace indexing,
storage, auth/session state, or other external systems, also apply
`./external-side-effect-reality-guard.md`.

## Default posture

Default to truthful live evidence.

If the user asks to test something, assume they expect the relevant behavior to
run for real: real endpoint, real scraper, real LLM/provider call, real auth
boundary, real persistence, real browser journey, or real workflow leg as
appropriate for the claim. Do not silently downgrade to a mock, fixture, replay,
stub, static projection, or simulated response because it is faster, cheaper, or
easier.

LLM/API cost is not a reason to hide a downgrade. Cost can justify proposing a
cheaper evidence mode, but the user must see and accept the weaker proof before
the run is described as tested.

## Evidence classes

Use the smallest class that honestly describes what happened:

| Class | Meaning | May prove | Must not prove |
|---|---|---|---|
| `static_mock` | Handwritten or static states with no runtime decision. | Copy, layout, UX comprehension. | Runtime behavior, data flow, provider calls. |
| `artifact_replay` | Previously captured outputs replayed through UI or projection code. | UI handling of known cases, projection stability. | Fresh scrape, fresh LLM/provider behavior, current endpoint health. |
| `unit_mocked` | Unit test with mocks/stubs for dependencies. | Local branching, mapping, validation logic. | Cross-layer integration or external behavior. |
| `integration_local` | Real local chain across app layers, with external services mocked or local. | App-layer interaction and contract wiring. | Live provider or production-environment behavior. |
| `live_local` | Local app calling real configured services or providers. | Fresh endpoint, scraper, LLM/API, auth, workflow leg, subject to local config. | Production readiness by itself. |
| `production_like` | Staging/production-style run with real deployment, auth, rate limits, persistence, and observability. | Shipping readiness for the covered scope. | Untested branches, tenants, regions, or failure modes. |
| `manual_user_verified` | The user verified a leg the agent cannot drive. | That specific human-observed leg. | Automated reproducibility. |

## Required UX

Before a non-live test or prototype is used for a user-facing claim, tell the
user plainly:

- what mode will run (`static_mock`, `artifact_replay`, etc.)
- why that mode is being proposed
- what it proves
- what it explicitly does not prove
- what live check remains before implementation, merge, or production readiness

If the user does not answer or continues with unrelated instructions, do not
upgrade the result into a live claim.

## Planning rules

Plans must attach an evidence class to every feature-bearing test scenario or
verification gate whose result could be confused with a stronger class.

For each scenario, include:

- expected evidence class
- whether the default should be live or a deliberately cheaper prototype mode
- `proves`
- `does_not_prove`
- live follow-up gate, when the first pass is mock/replay

Mock/replay scenarios are acceptable for early UX learning, but they must be
paired with a separate live gate before any claim about runtime, scraping, LLM
judgment, workflow start, persistence, auth, rate limits, or production
readiness.

## Execution rules

Before marking a task done, audit the evidence actually produced:

1. What ran for real?
2. What was mocked, replayed, projected, cached, fixture-backed, or simulated?
3. Did the browser/network/server/trace evidence match the intended evidence
   class?
4. Is the response time suspiciously fast for a claimed scrape, LLM/provider
   call, email delivery, payment, or workflow? If yes, inspect network/server
   logs or traces before calling it live.
5. Is the final user-facing claim worded at the evidence class actually reached?

If a live test is blocked by auth, cost, missing credentials, rate limits,
provider availability, or safety controls, report the block. Do not replace it
with replay and call the live path tested.

## Reporting rules

Every final test or readiness summary must distinguish:

- `Verified live`
- `Verified by replay/mock`
- `Not tested`
- `Blocked`

For each material claim, report `proves` and `does_not_prove` when there is any
risk the user could infer a stronger result than the evidence supports.

Good:

> `artifact_replay` verified that the UI guides users through `focus_required`.
> It does not prove the current scraper or Azure admission prompt returns that
> result live.

Bad:

> URL admission is tested.

## Browser-specific rule

Browser evidence proves what the browser observed, not automatically what the
backend did. If the claim depends on a backend call, provider call, scrape,
email, payment, persistence, or workflow side effect, pair browser observation
with network, server, database, provider, or trace evidence appropriate to the
claim.

If a browser test uses request interception, `page.route`, static API fixtures,
placeholder service credentials, or any mocked backend response, classify the
backend leg as `mocked_backend`/`Verified by replay/mock`. It may prove UI
payload shape and user interaction, but it does not prove the real endpoint,
server-only environment, auth boundary, Supabase write/read, provider call,
workflow start, or trace persistence. Before opening a manual test URL for a
user, run a same-runtime preflight for the relevant backend class or explicitly
label the session `ui_only`/`mocked_backend`.

## Claim integrity receipt

If a reader could infer a stronger result than the evidence supports, include a
compact claim-integrity receipt:

```text
Claim: <claim_class>: <specific subject>
Evidence class: <class from this guard>
Evidence: <paths, commands, traces, screenshots, logs, provider run IDs, or database proof>
Proves: <narrow claim actually proven>
Does not prove: <stronger claims still open>
Residual risk: <remaining gap or not_applicable>
```
