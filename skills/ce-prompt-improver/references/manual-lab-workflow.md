# Manual CE prompt lab workflow

This reference is the practical runbook for the manual mode of `ce-prompt-improver`.

## Operating stance

The manual lab improves prompts and prompt-adjacent contracts before production wiring. It is allowed to create candidate prompt text, candidate schema blocks, test cases, review data, and promotion packets. It does not silently edit production runtime files.

Use plain labels for source status:

| Label | Meaning |
|---|---|
| `current_runtime_evidence` | Observed in active runtime, rendered prompt, trace, parser output, handoff, or validated code. |
| `target_contract` | Accepted as the desired contract, but not necessarily implemented yet. |
| `proposed_shape` | Candidate under review. |
| `example_only` | Example for explanation; not evidence. |

## Round loop

Each round should answer one question:

```text
Does candidate B better satisfy the target behavior than baseline A without breaking must-survive facts or guardrails?
```

Recommended round steps:

1. Record the goal in `round-brief.md`.
2. Copy or reference the baseline prompt/contract.
3. Write one candidate variant with a named improvement lever.
4. Select representative cases and edge cases.
5. Choose the provider profile for the operation and store it as a round artifact.
6. Run the available evaluator, replay, provider call, or manual fixture.
7. Run deterministic prompt preflight for each rendered prompt when provider behavior is in scope.
8. Capture outputs and source classes.
9. Build `html/assets/data.json` for the A/B review surface using the shared static review contract, sample data, or builder script.
10. Record the human decision.
11. Either revise in a new round or write a promotion packet.

Default command path:

```bash
python <skill>/scripts/scaffold_lab.py --slug <slug> --source <source-or-brief> --goal "<goal>"
cp <skill>/templates/round-results.template.json <round>/round-results.json
python <skill>/scripts/preflight_prompt_contract.py --prompt <rendered-prompt.txt> --variant-id <id> --provider-route <route> --out <round>/artifacts/preflight/<case>__<variant>.json
python <skill>/scripts/build_review_data.py --round-results <round>/round-results.json --out <round>/html/assets/data.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --out <round>/artifacts/review-data-validation.json
python <skill>/scripts/render_review_html.py <round>/html/assets/data.json
python <skill>/scripts/open_review_surface.py <round>/html/index.html --print-only
```

The static snapshot is shareable only after the validator passes and `html/index.html` exists. The snapshot is only an A/B test if `validate_review_data.py --require-real-ab` passes; that validator is necessary but not sufficient for promotion, which also needs trace integrity, provider preflight, visible source classes, and an honest HITL decision.

For provider-backed rounds, also read `provider-best-practice-routing.md` and run:

```bash
python <skill>/scripts/preflight_prompt_contract.py --prompt <rendered-prompt.txt> --variant-id <id> --provider-route <route> --out <round>/artifacts/preflight/<case>__<variant>.json
```

Provider-profile and preflight artifacts must survive into `preflightChecks`; otherwise the review packet is incomplete. If preflight is produced after a draft data build, rebuild the data packet, re-run validation, and rerender the static HTML.

## Review packet contract

`html/assets/data.json` should be decision-support data, not a raw trace dump. Keep enough evidence for inspection, but organize it around the choice the human must make.

Before writing the packet, inspect the shared static review-surface contract, sample data, or generator script. For PromptReview-style surfaces, `variants` and `cases[].results` are UI-bearing fields, not optional decoration: without them the A/B comparison cannot choose left/right outputs.

Recommended top-level fields:

```json
{
  "variants": [],
  "campaign": {},
  "round": {},
  "goalProgress": {},
  "overallAnalysis": {},
  "decisionScorecard": {},
  "assistant_recommendation": {},
  "metricMatrix": [],
  "decisionMetrics": {},
  "interpretationNotes": [],
  "iterationPath": [],
  "traceIntegrity": {},
  "hitlDecision": {},
  "preflightChecks": [],
  "cases": [
    {
      "id": "case-id",
      "testIntent": {},
      "results": []
    }
  ]
}
```

Case entries should include the test intent, baseline output, candidate output, observed deltas, guardrail notes, and source class. If a metric is not available in the current repo, write `not_available` or `inconclusive` instead of inventing precision.

When builder and verifier scripts exist, prefer the repo's established flow:

1. Build `html/assets/data.json` from the round results.
2. Verify that the review data does not drift from request, rendered prompt, response, parsed output, metrics, trace, or artifact evidence.
3. Render `html/index.html` from the shared template and only then provide the static snapshot path.

The static renderer works for both daily experiment workspaces and scratch workspaces. A data packet in a hidden scratch directory is still useful as local evidence, but it is not a rendered review surface until `html/index.html` has been generated from it.

After the human decision, delete disposable rendered HTML if it is no longer needed:

```bash
python <skill>/scripts/cleanup_review_html.py <round>/html/index.html --decision <promote_candidate|revise_candidate|keep_baseline|split_candidate|inconclusive>
```

Keep `html/assets/data.json`, artifacts, validation reports, trace reports, and the promotion or inconclusive packet.

For CE Prompt Improver's own portable flow, use `round-results.json` as the editable source and generate `html/assets/data.json` from it. This keeps the human-editable test description separate from the UI-specific PromptReview shape.

## Real A/B minimum

A real A/B round needs, for every case and every compared variant:

- real `providerRoute` or artifact-replay route;
- real `model`, not `not_called`;
- real `durationMs`;
- system prompt and user prompt content or exact rendered prompt artifact;
- raw response, response text, parsed output and metrics artifacts;
- `artifactBase` or equivalent trace pointer;
- `evidenceClass` that is not static/layout-only.

If any of these are missing, do not ask for promotion. Record the round as a layout smoke, fixture check, or incomplete draft.

## Example target: customer-safe page context

When a stage already makes the admission decision but downstream UI needs a safer projection, the candidate should add only the smallest durable contract needed by that UI.

For example, a candidate may introduce a block like this as `proposed_shape`:

```json
{
  "dashboard_page_context": {
    "page_role_summary": "specific_offering_page | small_site_offering_surface | broad_company_page | product_index_or_portfolio | content_or_proof_page | unclear",
    "market_language_summary": "fits | potential_mismatch | global_or_region_agnostic | unclear",
    "customer_safe_context_note": "One short user-facing sentence in target_ui_language, max 180 characters.",
    "visible_basis": ["1-3 short observed signals, customer-safe, no internal diagnostics"]
  }
}
```

The round should explicitly reject adding a score, a new good/bad URL verdict, a hard readiness flag, or dashboard comments owned by a later stage unless the accepted goal says otherwise.

## Promotion packet shape

Use this compact structure when a candidate wins:

```markdown
# Prompt promotion packet

Status: accepted_candidate | revise_candidate | inconclusive

## Accepted delta

## Source status labels

## Must-survive facts

## Must-reject behaviors

## Evidence gathered

## What this proves

## What this does not prove

## Recommended CE next step
```

The recommended next step is usually `ce-plan` for cross-file implementation or `ce-work` for a small, well-bounded production change.
