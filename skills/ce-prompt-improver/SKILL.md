---
name: ce-prompt-improver
description: "This skill should be used when improving CE skill-chain, product, runtime, stage, System Prompt, User Prompt, output-schema, or data-model prompts through manual or autonomous Prompt Lab A/B testing before production wiring."
argument-hint: "[prompt target, stage, skill, plan/requirements path, run artifact, or campaign directory]"
disable-model-invocation: false
allowed-tools: Read, Write, Bash, Glob, Grep
---
<!-- TOKEN_BUDGET: 15000 -->

# CE Prompt Improver

Create a manual-first CE Prompt Lab for prompt and contract iteration. The skill adapts the proven prompt A/B review pattern to the Compound Engineering chain: `ce-brainstorm` defines the goal, `ce-plan` can shape implementation work after promotion, and `ce-work` only edits production after explicit acceptance. It also supports autonomous candidate-search and pipeline-gate mode when an upstream CE skill supplies a bounded goal, case matrix, provider profile, and stop rules.

This is a lab skill, not a production wiring shortcut. It helps the user compare baseline and candidate prompts, inspect evidence in a review surface, decide what to promote, and produce a handoff packet for later implementation. Use the included scripts and templates for scaffolding, Review-Data generation, validation, and route creation; do not handcraft a React packet from memory when the scripts can do it.

## When to Use

Use this skill when the user wants to:

- improve a prompt used by a CE skill, product runtime, workflow stage, LLM pipeline, provider request, or structured output contract;
- iterate a System Prompt, User Prompt, JSON schema, data model, parser-facing contract, or stage handoff before wiring it into production;
- turn a `ce-brainstorm` or `ce-plan` goal into a prompt experiment campaign;
- run a manual A/B comparison with rendered review evidence and a human promotion decision; a real A/B comparison requires real provider or artifact-replay runs, not static mocks;
- run autonomous A/B iterations until the prompt candidate reaches the accepted target, a budget expires, or a hard gate fails;
- act as a pipeline gate for `ce-plan`, `ce-work`, `ce-brainstorm`, or similar CE flows before production prompt-contract work is claimed ready;
- prepare a promotion packet for `ce-plan` or `ce-work` after the prompt candidate is accepted.

Do not use this skill as proof that production is wired, deployed, or ready. A lab result can support a promotion decision; production readiness belongs to the later implementation and evidence path.

## Process

### 1. Triage the target and load guards

Read the user's target, then classify the work as one or more of:

- `current_runtime_evidence`: active prompt/runtime/trace evidence already exists;
- `target_contract`: the user has accepted the shape as the build target;
- `proposed_shape`: candidate shape under exploration;
- `example_only`: explanatory sample, not an observed runtime fact.

If the work touches runtime prompts, model-visible data, provider requests, structured output, workflow stages, prompt A/B promotion, or production claims, read and apply `../shared/references/ce-runtime-prompt-contract-guard.md`.

If the result may support readiness, provider, workflow, trace, browser, or persistence claims, read and apply `../shared/references/evidence-claim-integrity-guard.md`.

Read `references/workspace-and-daily-room-guard.md` before creating any campaign under `docs/todo/**`. Never create a new current-date Tagesraum unless the user explicitly asks for that path.

If the lab will compare prompts, model calls, provider routes, search/retrieval behavior, or prompt-adjacent JSON contracts, read `references/provider-best-practice-routing.md` before writing variants or running evidence. A CE prompt round must choose a provider profile per operation, store that choice in the round artifacts, and expose the resulting preflight in the review surface.

### 2. Resolve the CE chain context

Look for an existing goal from `ce-brainstorm`, implementation target from `ce-plan`, or active work context from `ce-work`. Use those artifacts as grounding, but keep the prompt lab separate from production changes.

If no CE artifact exists, create a compact lab brief instead of forcing a full requirements or plan document. The brief should capture:

- the target behavior;
- the baseline prompt or contract;
- the candidate improvement lever;
- must-survive facts;
- must-reject behaviors;
- evidence classes available for this run;
- the intended downstream consumer.

If the skill is invoked by another CE skill, classify the call as `manual`,
`autonomous_candidate_search`, or `pipeline_gate`. Read
`references/autonomous-ab-testing.md` for autonomous or pipeline-gate calls.
Autonomous mode is allowed only when the upstream context supplies a bounded
goal, acceptance/case matrix, provider profile, budget, and stop condition. If
one of those is missing, create or update the lab brief and ask only for the
smallest missing decision instead of inventing it.

### 3. Create or resume the lab workspace

Prefer a project-local, inspectable workspace already used by the repo. If the active repo's review route only serves `html/assets/data.json` from specific directories, choose a route-allowed workspace before creating the campaign.

If the repo has no convention and no route restriction, use:

```text
.context/compound-engineering/ce-prompt-improver/<slug>/
```

When the active project uses durable daily experiment workspaces, follow that convention instead. Keep scratch state separate from production code. Do not give the user a rendered review route until the chosen workspace is accepted by that route or its data resolver.

Use the scaffolder unless resuming an existing campaign:

```bash
python <skill>/scripts/scaffold_lab.py --slug <slug> --source <source-or-brief> --goal "<goal>"
```

If the source is not already inside the intended `docs/todo/YYYY_MM_DD/` workspace, pass `--campaign` or `--day-dir` explicitly. The script intentionally falls back to `.context/compound-engineering/ce-prompt-improver/` instead of inventing a new date-based daily room.

Recommended workspace shape:

```text
<campaign>/
  campaign-state.json
  README.md
  01_intake/
  02_cases/
  03_rounds/
    round-01-<slug>/
      round-brief.md
      baseline/
      variant/
      comparisons/
      html/assets/data.json
  04_decisions/
  05_promotion-packets/
```

### 4. Build the baseline and candidate

Treat the current prompt as `A: baseline`. Create `B: candidate` with one primary improvement lever whenever possible. Examples:

- add a customer-safe projection block;
- tighten an output schema;
- separate runtime-only context from LLM-visible contract;
- preserve must-survive facts across a handoff;
- remove a confusing diagnostic or internal-only field from customer-facing output.

Do not mix prompt wording, schema changes, runtime parser changes, and dashboard copy in one candidate unless the user explicitly wants a bundle comparison.

### 5. Run evidence and preserve source classes

For every test case, write down the evidence class before evaluating it:

- `static_mock`
- `layout_smoke_not_ab_test`
- `artifact_replay`
- `unit_mocked`
- `integration_local`
- `live_local`
- `production_like`
- `manual_user_verified`

Keep these source classes separate:

- rendered prompt or candidate contract;
- parsed model output;
- runtime-only projection;
- handoff or trace artifact;
- UI/dashboard interpretation;
- human review decision.

Never present an example JSON shape as observed output unless it came from an actual run artifact. Never call `static_mock`, `layout_smoke`, fixture-only, or `model: not_called` data an A/B test. Those are only layout or script smokes.

For real manual A/B evidence, run every case/variant through a provider runner or replay existing artifacts. The CE runner loads `.env.local` by default so project-local provider keys are available without printing secrets. Use the OpenSpec-compatible runner for parity surfaces:

```bash
python <skill>/scripts/lab_runner.py --surface perplexity-agent --case <case.json> --variant-id <id> --system <system.txt> --user <user.txt> --out-dir <round>/artifacts/cases
```

The older CE-normalized runner remains available for direct CE result JSON:

```bash
python <skill>/scripts/provider_lab_runner.py --surface perplexity-agent --case <case.json> --variant-id <id> --system <system.txt> --user <user.txt> --out-dir <round>/artifacts/cases
```

Fixture mode is allowed only for script validation and must be labeled as fixture/layout evidence.

Choose a provider profile before the first run. Use `perplexity_sonar` for Perplexity/Sonar/Search/Agent routes, the concrete OpenAI/GPT profile when an OpenAI runtime/model is known, and `generic_llm` with a visible uncertainty note when the route is unknown. Pass the profile into prompt preflight and record the provider-profile artifact in the round. Provider rules are routed evaluation rules, not universal style preferences.

### 6. Build the review surface packet

The review packet must be usable for a rendered A/B comparison. If the active repo has a React review route for prompt A/B surfaces, discover its typed data contract, sample `html/assets/data.json`, or builder/verifier scripts before writing the packet. Do not hand-invent a "compatible" shape from memory.

For PromptReview-style surfaces, the packet must at least preserve the UI-bearing shape: `variants`, `cases`, each case's `results`, the baseline/right variant identifiers when required, and the decision-support fields below. If the repo exposes builder or trace-verifier scripts, use them and record the commands. If no verifier exists, run the route/data resolver or a local schema check before giving the user the link.

If the repo does not have a review route, produce the same decision packet plus a Markdown decision summary.

At minimum, the packet should include:

- campaign metadata and goal;
- baseline and candidate summaries;
- case-level outputs and deltas;
- metric or judge dimensions;
- guardrail pass/fail notes;
- source-class and trace-integrity notes;
- assistant recommendation;
- HITL decision fields;
- promotion packet pointer.

For a PromptReview-style React route from real provider/replay evidence, use the OpenSpec-compatible artifact contract first:

```bash
python <skill>/scripts/autonomous_prompt_loop.py --config <campaign>/01_intake/autonomous-loop-config.json
python <skill>/scripts/normalize_results_summary_from_artifacts.py --results <round>/artifacts/results-summary.raw.json --out <round>/artifacts/results-summary.json
python <skill>/scripts/build_review_surface_data.py --results <round>/artifacts/results-summary.json --out <round>/html/assets/data.json
python <skill>/scripts/merge_review_surface_overrides.py --data <round>/html/assets/data.json --overrides <review-enrichment.json> --out <round>/html/assets/data.json
python <skill>/scripts/verify_review_surface_trace.py --results <round>/artifacts/results-summary.json --data <round>/html/assets/data.json --out <round>/artifacts/trace-integrity-report.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --out <round>/artifacts/review-data-validation.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --require-real-ab
python <skill>/scripts/make_review_url.py <round>/html/assets/data.json
```

Run deterministic prompt preflight when rendered prompts exist:

```bash
python <skill>/scripts/preflight_prompt_contract.py --prompt <rendered-prompt.txt> --variant-id <id> --provider-route <route> --out <round>/artifacts/preflight/<case>__<variant>.json
```

For a PromptReview-style React route from the CE skill's normalized input format, use the lightweight builder:

```bash
cp <skill>/templates/round-results.template.json <round>/round-results.json
python <skill>/scripts/build_review_data.py --round-results <round>/round-results.json --out <round>/html/assets/data.json
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --out <round>/artifacts/review-data-validation.json
python <skill>/scripts/make_review_url.py <round>/html/assets/data.json
```

Read `references/react-review-data-contract.md` before editing `round-results.json`. If manual `data.json` edits are unavoidable, re-run `validate_review_data.py` before sharing the route.

Before calling the route an A/B test, also run:

```bash
python <skill>/scripts/validate_review_data.py <round>/html/assets/data.json --require-real-ab
```

If that command fails, call the output a layout smoke or artifact draft, not an A/B test.

For feature parity with `$openspec-prompt-optimizer`, a reviewable CE Prompt A/B HTML report must expose the same decision-support contract: real trace/provider artifacts, non-empty System/User prompts, provider responses, parsed outputs, metrics, `goalProgress`, `overallAnalysis`, `decisionScorecard`, `assistant_recommendation`, `metricMatrix`, `decisionMetrics`, `interpretationNotes`, `iterationPath`, `traceIntegrity`, `hitlDecision`, `preflightChecks`, `testIntent`, `cases[].testIntent`, and `roundNavigation`. If one of these fields is missing, either rebuild from the artifact set or label the surface as incomplete.

If the generic builder cannot derive richer review copy from the artifact summary alone, use `merge_review_surface_overrides.py` with an explicit enrichment/reference JSON. The override file is display and review support; the trace verifier still decides whether the displayed prompts, responses, parsed outputs, metrics, and artifact refs match the actual run artifacts.

If a replayed or imported `results-summary.json` does not byte-match its artifact files, do not weaken verification. Run `normalize_results_summary_from_artifacts.py` first and treat the normalized summary as the trace-backed input.

If the rendered review surface is part of the claim, run a local browser smoke and record:

- tool route and runtime class;
- target URL;
- screenshot path or snapshot evidence;
- console-error status;
- cleanup statement for any owned tab/page.

### 7. Run HITL promotion

Ask the user to choose one of:

- promote candidate;
- revise candidate;
- keep baseline;
- split the candidate into smaller experiments;
- stop as inconclusive.

Do not write production prompt files, schemas, runtime parsers, or dashboard consumers from the lab alone. Promotion creates a packet for `ce-plan` or `ce-work`; implementation is a separate step with its own evidence.

In autonomous mode, do not ask after every round. Continue while the iteration
budget remains and the next round can improve a failed gate with one bounded
lever. Stop immediately when a hard gate fails in a way the lab cannot repair,
the candidate passes promotion threshold, or the budget is exhausted. Then write
either a promotion packet or an inconclusive packet and expose the rendered
review URL with round navigation for every attempted iteration.

### 8. Produce the promotion packet

When the user accepts a candidate, write a compact handoff under `05_promotion-packets/` with:

- accepted prompt or contract delta;
- exact source status labels;
- must-survive facts;
- must-reject behaviors;
- affected files or likely consumers;
- evidence gathered and what it proves;
- what it does not prove;
- recommended `ce-plan` or `ce-work` next step.

## Resources

- Manual lab workflow: `references/manual-lab-workflow.md`
- CE skill-chain integration: `references/ce-skillchain-integration.md`
- Autonomous A/B testing: `references/autonomous-ab-testing.md`
- React review data contract: `references/react-review-data-contract.md`
- Provider best-practice routing: `references/provider-best-practice-routing.md`
- Workspace and daily-room guard: `references/workspace-and-daily-room-guard.md`
- Round-results template: `templates/round-results.template.json`
- Autonomous loop config template: `templates/autonomous-loop-config.template.json`
- Promotion packet template: `templates/promotion-packet.template.md`
- Scaffold script: `scripts/scaffold_lab.py`
- Autonomous prompt loop runner: `scripts/autonomous_prompt_loop.py`
- Review data builder: `scripts/build_review_data.py`
- OpenSpec-compatible review data builder: `scripts/build_review_surface_data.py`
- Results summary normalizer: `scripts/normalize_results_summary_from_artifacts.py`
- Review data validator: `scripts/validate_review_data.py`
- Review trace verifier: `scripts/verify_review_surface_trace.py`
- Review enrichment merger: `scripts/merge_review_surface_overrides.py`
- Review URL helper: `scripts/make_review_url.py`
- OpenSpec-compatible lab runner: `scripts/lab_runner.py`
- Provider lab runner: `scripts/provider_lab_runner.py`
- Prompt preflight: `scripts/preflight_prompt_contract.py`
- Response evaluator: `scripts/evaluate_response.py`
- OpenSpec-compatible response evaluator: `scripts/evaluate_prompt_run.py`
- WSL-safe static opener: `scripts/open_review_surface.py`
- Script self-test: `scripts/self_test.py`
- Shared guard for runtime prompt contracts: `../shared/references/ce-runtime-prompt-contract-guard.md`
- Shared guard for evidence claims: `../shared/references/evidence-claim-integrity-guard.md`
