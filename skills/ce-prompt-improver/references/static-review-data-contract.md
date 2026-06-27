# Static review data contract

The CE Prompt Improver renders Prompt A/B reviews as static `html/index.html`
snapshots using the shared Prompt Improver template. Before a snapshot is
shared, the lab must produce and validate a PromptReview-compatible
`html/assets/data.json`.

Required review-shape fields:

- `variants`: baseline and candidate entries with stable `id`, `label` or `name`, and a short description.
- `leftVariantId`: baseline variant id when the template expects it.
- `defaultRightVariant`: candidate variant id when the template expects it.
- `campaign`, `round`, `goalProgress`, `overallAnalysis`, `decisionScorecard`, `assistant_recommendation`, `metricMatrix`, `decisionMetrics`, `interpretationNotes`, `iterationPath`, `traceIntegrity`, `hitlDecision`, `preflightChecks`.
- `cases`: each case needs `id`, `testIntent`, and `results`.
- `cases[].results`: each result needs `variantId`, output/response text, parsed output status, metrics, source class, and artifact pointers when available.
- `roundNavigation`: include every available round so a multi-round campaign is navigable from the rendered static snapshot.

Provider profile evidence must be visible for real A/B rounds that touch
provider behavior. `preflightChecks` must include provider fit, routed
best-practice status, simplicity, anti-overfit/hardcoding risk, generalization
evidence, and any provider uncertainty.

Canonical source-class fields:

- Top-level round claim: `evidenceClass`.
- Case/result evidence: `cases[].results[].sourceClass` when present, falling back to result metadata from the builder.
- Trace status: `traceIntegrity`.
- Human decision status: `hitlDecision`.

Default static render flow:

```bash
python <skill>/scripts/preflight_prompt_contract.py --prompt <rendered-prompt.txt> --variant-id <id> --provider-route <route> --out <round>/artifacts/preflight/<case>__<variant>.json
python <skill>/scripts/build_review_data.py --round-results <round>/round-results.json --out <round>/html/assets/data.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --out <round>/artifacts/review-data-validation.json
python <skill>/scripts/render_review_html.py <round>/html/assets/data.json
python <skill>/scripts/open_review_surface.py <round>/html/index.html --print-only
```

For OpenSpec-compatible artifact summaries:

```bash
python <skill>/scripts/preflight_prompt_contract.py --prompt <rendered-prompt.txt> --variant-id <id> --provider-route <route> --out <round>/artifacts/preflight/<case>__<variant>.json
python <skill>/scripts/build_review_surface_data.py --results <round>/artifacts/results-summary.json --preflight <round>/artifacts/preflight/<case>__<variant>.json --out <round>/html/assets/data.json
python <skill>/scripts/verify_review_surface_trace.py --results <round>/artifacts/results-summary.json --data <round>/html/assets/data.json --out <round>/artifacts/trace-integrity-report.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --out <round>/artifacts/review-data-validation.json
python <skill>/scripts/render_review_html.py <round>/html/assets/data.json
python <skill>/scripts/open_review_surface.py <round>/html/index.html --print-only
```

Only write `data.json` manually when the builder cannot represent the needed
structure. If manual editing is necessary, run the validator and rerender
`html/index.html` before sharing the snapshot.

Cleanup rule:

```bash
python <skill>/scripts/cleanup_review_html.py <round>/html/index.html --decision <promote_candidate|revise_candidate|keep_baseline|split_candidate|inconclusive>
```

Delete rendered static HTML snapshots after the top variant is selected and the
snapshot is no longer needed. Keep the evidence packet (`data.json`, artifacts,
trace reports, validation reports, and promotion/inconclusive packet). Use
`--keep-as-export-archive` only when the HTML itself is intentionally retained
as a review artifact.

Before calling a review snapshot an A/B test, run:

```bash
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --require-real-ab
```

This validator is necessary but not sufficient. Promotion also requires trace
integrity, provider preflight, visible source classes, and an honest HITL
decision. If any gate fails, call the snapshot a layout smoke, artifact draft,
or incomplete review packet, not a real A/B test.
