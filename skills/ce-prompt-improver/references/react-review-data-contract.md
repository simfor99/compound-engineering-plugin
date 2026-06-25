# React review data contract

The CE Prompt Improver must not handwave the rendered review surface. Before a route is shared, the lab must produce and validate a PromptReview-compatible `html/assets/data.json`.

## Required shape

- `evidenceClass`: use `layout_smoke_not_ab_test` for render-only checks; use provider or replay evidence labels for real A/B tests
- `variants`: at least baseline and candidate, with stable `id`
- `leftVariantId`: baseline variant id when the local route expects it
- `defaultRightVariant`: candidate variant id when the local route expects it
- `cases`: at least one case
- `cases[].results`: one result per variant
- `results[].variantId`: must match a variant id
- `results[].parsedOk`: boolean
- `results[].metrics.schema_ok`: required when `parsedOk` is true
- `results[].prompt`: system/user prompt or a truthful reference
- `results[].parsedOutput`: observed or clearly marked static/mock output
- `results[].providerRoute`, `model`, `providerCalledAt`, `durationMs`, and artifact pointers when a real A/B run is claimed
- `roundNavigation`: include every available round so a five-round campaign is navigable from the rendered React surface
- `traceIntegrity`, `hitlDecision`, `decisionScorecard`, and `notProven`: required for honest promotion discussion
- OpenSpec-parity fields for reviewable A/B rounds: `goalProgress`, `overallAnalysis`, `assistant_recommendation`, `metricMatrix`, `decisionMetrics`, `interpretationNotes`, `iterationPath`, `preflightChecks`, `testIntent`, and `cases[].testIntent`
- Header parity fields: `scorecards` must provide the expanded-header KPI overview, while the collapsed header must still expose detail metadata such as evidence class, case count, variants, prompt contract, testset, and round id. A rendered report that only shows detail metadata and no KPI overview is incomplete.
- Every real result must be traceable to the six artifact files: request, rendered prompt, raw response, response text, parsed output, and metrics
- Provider profile evidence must be visible for real A/B rounds that touch provider behavior. `preflightChecks` must include provider fit, routed best-practice status, simplicity, anti-overfit/hardcoding risk, generalization evidence, and any provider uncertainty.

## Build rule

For real provider or artifact-replay evidence, prefer the OpenSpec-compatible path:

```bash
python <skill>/scripts/normalize_results_summary_from_artifacts.py --results <round>/artifacts/results-summary.raw.json --out <round>/artifacts/results-summary.json
python <skill>/scripts/build_review_surface_data.py --results <round>/artifacts/results-summary.json --out <round>/html/assets/data.json
python <skill>/scripts/merge_review_surface_overrides.py --data <round>/html/assets/data.json --overrides <review-enrichment.json> --out <round>/html/assets/data.json
python <skill>/scripts/verify_review_surface_trace.py --results <round>/artifacts/results-summary.json --data <round>/html/assets/data.json --out <round>/artifacts/trace-integrity-report.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --require-real-ab
python <skill>/scripts/make_review_url.py <round>/html/assets/data.json
```

`merge_review_surface_overrides.py` may copy richer review/display fields such as `roundNavigation`, `testIntent`, `scorecards`, `interpretationNotes`, and `decisionMetrics` from an explicit enrichment JSON. It must not replace trace verification; always run `verify_review_surface_trace.py` after merging.

Imported replay summaries may contain stale embedded prompt, response, parsed-output, or metrics fields. If so, run `normalize_results_summary_from_artifacts.py` and build from the normalized summary. The artifact files are the trace truth.

Provider best-practice findings are review evidence, not decoration. A real A/B report that omits provider-profile/preflight evidence must be labeled incomplete, even when the provider calls themselves succeeded.

For lightweight CE-normalized layout drafts, use:

```bash
python <skill>/scripts/build_review_data.py --round-results <round>/round-results.json --out <round>/html/assets/data.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json
python <skill>/scripts/make_review_url.py <round>/html/assets/data.json
```

Only write `data.json` manually when the builder cannot represent the needed structure. If manual editing is necessary, run the validator before sharing the route.

## Claim rule

`static_mock`, `layout_smoke`, and `layout_smoke_not_ab_test` can prove layout shape, contract readability, and HITL review usefulness. They cannot be called A/B tests and cannot prove provider stability, production readiness, Customer API readiness, latency, token cost, or persistence behavior.

Before sharing a review route as an A/B test, run:

```bash
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --require-real-ab
```

This must fail when results use `model: not_called`, `providerRoute: static_mock`, missing `durationMs`, or static/layout-only evidence.

A red provider-fit or best-practice preflight finding blocks promotion unless the HITL decision explicitly accepts the risk and explains why the observed run evidence still supports the candidate.
