# CE subagent boundaries

Use this reference when CE skills spawn or consume subagents.

## Core rule

Subagents provide evidence, perspective, and parallel analysis. They do not own
canonical truth.

The main agent owns:

- final artifact creation and edits;
- final verdicts and readiness claims;
- validator selection and interpretation;
- user-facing decisions and trade-off framing;
- reconciliation of contradictions between agents;
- any claim that a goal, plan, review, or implementation is complete.

## Allowed subagent ownership

Subagents may own bounded work packages when explicitly scoped:

- inspect a file set and report findings;
- implement a disjoint code slice;
- run an independent review lens;
- verify a specific artifact or command;
- summarize evidence with paths and commands.

They must not be treated as authoritative when:

- their cited files or commands were not checked by the main agent;
- they infer state from memory instead of current files;
- they propose deleting protected CE artifacts;
- they expand scope beyond the assigned package;
- they make readiness claims without evidence-class and claim-class boundaries.

## Required handoff from subagents

Ask for:

- files inspected or changed;
- commands run and result;
- findings with severity and evidence;
- uncertainty and skipped scope;
- whether any conclusion depends on mocked, replayed, or indirect evidence.

## Main-agent closeout

Before finalizing, the main agent must:

1. read or inspect any cited canonical artifact needed for the final claim;
2. deduplicate and reconcile findings;
3. run or cite validators appropriate to the claim;
4. explicitly mark unresolved subagent disagreement or uncertainty.
