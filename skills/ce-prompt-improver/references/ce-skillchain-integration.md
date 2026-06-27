# CE skill-chain integration

`ce-prompt-improver` sits between CE thinking artifacts and implementation. It creates evidence for a prompt decision; it does not replace the later build path.

## Upstream inputs

Use these inputs when present:

| Upstream source | How to use it |
|---|---|
| `ce-brainstorm` requirements | Treat the goal, non-goals, user-visible behavior, and acceptance examples as the lab objective. |
| `ce-plan` plan | Treat implementation units, prompt sidecars, contracts, and test scenarios as the bounded target. |
| `ce-work` context | Use current changed files and discovered runtime evidence as baseline, but do not mutate production unless the user explicitly converts the lab result into work. |
| Runtime traces or replay artifacts | Use as evidence cases; keep trace-only data separate from prompt-visible data. |

If none exist, write a compact lab brief instead of starting a full planning process. The point is to unblock prompt iteration, not to add ceremony.

## Downstream outputs

The skill should end with one of these outcomes:

| Outcome | Meaning | Next action |
|---|---|---|
| `promote_candidate` | Human accepted the candidate prompt or contract. | Write a promotion packet, then route to `ce-plan` or `ce-work`. |
| `revise_candidate` | Candidate is promising but not ready. | Start the next lab round. |
| `keep_baseline` | Baseline is better or safer. | Record why and stop. |
| `split_candidate` | Candidate mixed too many concerns. | Create smaller variants. |
| `inconclusive` | Evidence is too weak. | Add cases, improve evaluator, or stop honestly. |

For autonomous or pipeline-gate calls, also write `autonomous-run-state.json`
with the current status, budget, rounds attempted, latest static review HTML path,
latest review data path, expected cleanup receipt path, stop reason, failed gates,
and accepted candidate if any. This state lets `ce-plan` or `ce-work` resume the
gate without reconstructing decisions from chat.

## Boundary with ce-plan

Use `ce-plan` after the lab when:

- the accepted delta touches multiple runtime layers;
- schemas, validators, prompts, projections, dashboard code, and tests must move together;
- there are architecture or rollout decisions;
- the implementation needs a durable task breakdown.

Do not force `ce-plan` before the lab when the user simply wants to compare prompts manually.

When `ce-plan` is the caller, use the plan's prompt-contract target and test
matrix as the gate contract. The plan should treat the Prompt Lab as a
verification or promotion unit before production wiring, not as implementation
proof by itself.

## Boundary with ce-work

Use `ce-work` after the lab when:

- the accepted change is small and well-scoped;
- the likely files are known;
- the production prompt profile and repo entrypoints are resolved;
- evidence expectations are clear.

`ce-work` owns production edits and verification. `ce-prompt-improver` owns the lab evidence and promotion packet.

When `ce-work` is the caller, run `ce-prompt-improver` as a blocking gate if the
task changes prompts, schemas, output contracts, or dashboard projections whose
correctness depends on LLM/provider behavior and no accepted lab packet already
exists. A failed or inconclusive gate blocks readiness claims unless Simon
explicitly accepts the residual risk.

## Boundary with ce-optimize

Use `ce-optimize` for broad metric optimization outside prompt contracts, or
when the search space is not prompt/schema/provider-output specific. Use
`ce-prompt-improver` for prompt-contract A/B loops because it owns rendered
PromptReview packets, provider preflight, trace integrity, and promotion
handoffs for CE prompts.
