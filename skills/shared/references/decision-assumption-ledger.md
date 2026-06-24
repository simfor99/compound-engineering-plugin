# CE decision and assumption ledger

Use this reference when a CE workflow could otherwise turn an assumption into a
decision without the user noticing.

## Trigger

Apply this ledger when work contains material uncertainty about:

- product, architecture, governance, risk, security, cost, release, data flow,
  prompt/runtime, evidence, or scope decisions;
- a user-owned decision that would change the accepted outcome;
- an assumption that downstream `ce-plan`, `ce-work`, `ce-code-review`, or
  `ce-doc-review` may later treat as settled.

Do not use it for trivial naming, formatting, or obvious implementation
details that the current skill can safely decide.

## Ledger classes

| Class | Meaning | Required handling |
|---|---|---|
| `repo_evidence_pending` | The answer should be discoverable from local files, docs, tests, git, or live evidence. | Inspect evidence before asking the user. |
| `carry_visible` | A low-risk assumption is acceptable, but must remain visible. | Record the assumption, consequence, and fallback. |
| `clarify_first` | Continuing could build the wrong thing or claim the wrong proof. | Ask the user before implementation or readiness claims. |
| `user_decision` | Simon owns the decision because it changes product, architecture, governance, cost, release, or risk. | Present options and wait for the decision. |
| `deferred_decision` | The decision is real but intentionally out of current scope. | Record the deferral and what future work must resolve. |

## Minimum entry

```text
Decision/Assumption: <short name>
Class: repo_evidence_pending|carry_visible|clarify_first|user_decision|deferred_decision
Source: <user message, plan section, repo file, or evidence path>
Why it matters: <what changes if wrong>
Current stance: <what CE will assume or ask>
Required before: planning|implementation|review|ship|not_applicable
Resolution: unresolved|resolved:<summary>|deferred:<follow-up>
```

## Skill behavior

- `ce-brainstorm` records material open decisions in requirements or working
  notes instead of smoothing over them.
- `ce-plan` converts unresolved `clarify_first` or `user_decision` entries into
  explicit questions or plan blockers. It may carry `carry_visible` entries only
  when the plan names the consequence and verification point.
- `ce-doc-review` treats a hidden material assumption as a finding. A document
  is allowed to defer a decision only when the deferral names the downstream
  gate it blocks.
- `ce-work` must not implement through unresolved `clarify_first` or
  `user_decision` entries unless the user has explicitly accepted the risk for
  this run.

## Reporting

When this ledger is active, final summaries should include:

```text
Decision/Assumption Ledger: loaded|not_applicable
Resolved: [...]
Carried visible: [...]
Blocked or deferred: [...]
```
