# Autonomous CE prompt A/B testing

Autonomous mode is a controlled Prompt Lab loop. It may create candidate
prompts, run provider-backed or artifact-replay comparisons, build rendered
review packets, and write promotion packets. It must not silently wire a
candidate into production.

## Modes

| Mode | Meaning | Human role |
|---|---|---|
| `manual` | Human and agent choose one round at a time. | Human reviews every round and decides. |
| `autonomous_candidate_search` | Agent iterates candidates until gates pass or budget ends. | Human reviews the final promotion or inconclusive packet. |
| `pipeline_gate` | Called from `ce-plan`, `ce-work`, or another CE skill before prompt-contract production work proceeds. | Human is only interrupted for missing inputs, failed gates, or promotion approval. |

## Required inputs

Autonomous mode needs a bounded target. If these are missing, fall back to a
manual lab brief or ask for the smallest missing item.

- Goal statement from `ce-brainstorm`, `ce-plan`, `ce-work`, or a compact lab brief.
- Baseline prompt, schema, output contract, or runtime behavior to compare as A.
- Candidate lever or allowed lever set for B, one primary lever per round.
- Case matrix with must-survive facts, must-reject behaviors, evidence class,
  and target outcome for each readiness-bearing case.
- Provider profile and best-practice route from `provider-best-practice-routing.md`.
- Iteration budget: `max_rounds`, `max_variants_per_round`, provider/cost budget,
  and stop condition.
- Promotion threshold: hard gates plus score dimensions that decide whether B
  is accepted, revised, split, or rejected.

## Loop contract

Run the loop as a sequence of honest, inspectable rounds:

1. Load the source goal, source labels, provider profile, and case matrix.
2. Select one improvement lever for the round.
3. Create candidate B in the lab workspace only.
4. Render the exact System/User prompts or prompt-adjacent contract artifacts.
5. Run every case and compared variant through real provider calls or accepted
   artifact replay. Fixture or static data may only validate scripts/layout.
6. Run provider preflight and response evaluation for each rendered prompt.
7. Build `html/assets/data.json` with round navigation and provider timestamps.
8. Validate the report with `validate_review_data.py --require-real-ab` and
   trace verification when artifact inputs exist.
9. Evaluate hard gates and score dimensions.
10. If gates pass, write a promotion packet and stop.
11. If gates fail and budget remains, identify the smallest failing lever and
    create the next round.
12. If budget is exhausted, write an inconclusive packet with the best observed
    candidate, failed gates, and recommended next action.

The deterministic runner is:

```bash
python <skill>/scripts/autonomous_prompt_loop.py --config <campaign>/01_intake/autonomous-loop-config.json
```

Use `templates/autonomous-loop-config.template.json` as the manifest shape. The
runner expects pre-authored baseline and candidate prompt files per round. The
calling LLM/skill may create the next candidate between runs, but the runner
does not invent prompt text by itself.

`campaignDir` is repo-relative by default, so `docs/todo/2026_06_04/...`
stays anchored under the supplied `--repo-root`. Use `./...` or `../...` only
when a campaign directory should intentionally be relative to the config file.

## Hard gates

A candidate cannot be promoted from autonomous mode unless all applicable gates
pass. A gate marked `not_claimed` or `deferred` is accepted as an honest boundary
label, but it is not a pass state; the autonomous runner must write an
inconclusive packet instead of silently promoting the candidate:

- Real A/B evidence passes `validate_review_data.py --require-real-ab`.
- Every readiness-bearing case matrix row is `passed`, `not_applicable`, or
  explicitly `not_claimed`/`deferred`; smoke subsets do not prove full readiness.
- Provider profile and prompt preflight are present for provider-backed runs.
- System Prompt, User Prompt, provider response, parsed output, metrics, artifact
  refs, and provider timestamps are visible in the review data.
- Review HTML exposes round navigation for all autonomous iterations.
- Trace verification passes when artifact summaries were normalized from files.
- No production prompt, schema, runtime parser, dashboard consumer, or workflow
  wiring is changed unless the user explicitly starts a follow-up `ce-work`
  implementation step.

## Required artifacts

Each autonomous campaign should keep this minimum state:

```text
<campaign>/
  campaign-state.json
  autonomous-run-state.json
  01_intake/
  02_cases/
  03_rounds/
    round-01-<slug>/
      round-brief.md
      baseline/
      variant/
      artifacts/
      html/assets/data.json
    round-02-<slug>/
      ...
  04_decisions/
  05_promotion-packets/
```

`autonomous-run-state.json` should record current status, budget, evaluated
rounds, latest review URL, stop reason, accepted candidate if any, and failed
gates. The rendered review packet is the human inspection surface; the promotion
packet is the implementation handoff.

## CE skill-chain hooks

- `ce-brainstorm` defines the optimization target: user-visible goal,
  acceptance matrix, must-survive facts, must-reject behaviors, evidence class,
  non-goals, and whether autonomous Prompt Lab work is allowed.
- `ce-plan` turns that target into a bounded implementation or verification
  unit. For material prompt-contract changes, it should plan a CE Prompt
  Improver gate before production wiring.
- `ce-work` runs the gate when executing prompt-contract-bearing work whose
  correctness depends on LLM/provider behavior. A failed or inconclusive gate
  blocks readiness claims unless Simon explicitly accepts the risk.

## Safety defaults

- Load provider keys through the project runner or `.env.local`; never print
  secrets.
- Do not create a new `docs/todo/<today>` Tagesraum unless Simon explicitly asks
  for a new day room.
- Prefer the existing campaign workspace when one exists.
- Do not convert static mocks, layout smokes, or fixture-only data into A/B
  claims.
- Keep source classes separate: prompt-visible data, runtime-only data,
  trace-only artifacts, dashboard interpretation, and human decisions.
