# Elons Principles order-of-operations guard

Use this reference when a CE workflow could otherwise professionalize the wrong
thing: clarify, document, plan, optimize, accelerate, or automate work before
checking whether the requirement or process step should exist.

The name is a mnemonic from Elon Musk's five-step engineering algorithm, not an
authority claim. Apply the sequence because the order is useful:

1. Make the requirements less dumb.
2. Delete a part or process step.
3. Simplify or optimize.
4. Accelerate cycle time.
5. Automate.

## Trigger

Apply this guard when work includes any of:

- ambiguous or expandable requirements;
- new workflow, process, pipeline, stage, agent, prompt chain, or automation;
- scope that exists mainly because an earlier system shape assumed it;
- optimization, speed, throughput, orchestration, or parallelization;
- a user request to "integrate", "scale", "automate", "standardize",
  "systematize", or "make the chain do this";
- a plan with implementation units that mostly support each other instead of
  directly serving the user-visible outcome.

Do not use it for trivial mechanical edits where scope is already fixed and the
change has no meaningful carrying cost.

## Core rule

Never skip forward in the sequence:

| Step | Question | Bad shortcut it prevents |
|---|---|---|
| Requirement | Is this the real requirement, or an inherited assumption? | Building the wrong thing cleanly. |
| Delete | What part, process step, field, hook, agent, or claim can disappear? | Optimizing unnecessary complexity. |
| Simplify | Can the kept part become smaller, clearer, or more direct? | Preserving accidental structure. |
| Accelerate | Is the remaining loop stable enough to make faster? | Speeding up churn or rework. |
| Automate | Is the remaining process understood and repeatable? | Automating a brittle workaround. |

If a later step looks attractive, first state why the earlier steps are already
satisfied or not applicable.

## Skill behavior

### `ce-brainstorm`

Use this as a requirements and scope-subtraction guard:

- pressure-test the user's requested shape against the real problem;
- ask for the smallest version that still creates real value when an attachment
  gap is present;
- include at least one delete/smaller-form option when proposing approaches for
  expandable work;
- avoid writing requirements for process steps, agents, fields, or automation
  that only exist to support an untested solution shape;
- record real user-owned scope decisions in the decision/assumption ledger
  instead of silently deleting them.

### `ce-plan`

Use this as an implementation-subtraction guard:

- before finalizing implementation units, scan for units that exist only because
  another unit added avoidable complexity;
- defer adjacent cleanup, platform work, or automation that is not required for
  the confirmed outcome;
- simplify the chosen implementation shape before adding cycle-time or
  orchestration improvements;
- require a clear reason before planning automation, agent dispatch,
  parallelization, or reusable process machinery;
- preserve requirements traceability when deleting scope: deletion must be a
  deliberate scope decision, not an accidental drop.

### `ce-work`

Use this lightly during execution:

- do not reopen settled product scope just because a smaller path appears;
- do flag a plan-risk if implementation reveals that a unit mainly supports
  avoidable complexity;
- do not add automation, scripts, subagents, or broad parallelism unless the
  remaining process is stable enough to benefit from it.

### `ce-compound`

When a session learns that deleting, narrowing, or de-automating was the useful
move, capture that as reusable knowledge rather than only documenting the final
positive implementation.

## Output expectations

When this guard materially changes a requirement, plan, or execution stance,
make the change visible:

```text
Elons Principles Guard: applied
Requirement check: <kept/reframed/deferred>
Deleted or avoided: <part/process/scope/automation, or none with reason>
Simplified before speed/automation: <yes/no/not_applicable>
Automation stance: <not_needed/deferred/planned_with_reason>
```

For lightweight work, a one-line note is enough. For Standard or Deep
brainstorms and plans, fold the result into scope boundaries, assumptions,
approach rationale, implementation units, or deferred follow-up work.

## Non-goals

- This guard does not override safety, security, evidence, compliance,
  accessibility, or user-owned decisions.
- Deleting scope is not the same as dropping required behavior silently.
- Simplicity is not anti-quality: low-cost polish, diagnostics, tests, and
  observability are good when their carrying cost is low and their value is
  clear.
- Automation is not bad. Premature automation is the failure mode.
