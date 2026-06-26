# CE quality gates

Use this reference when a plan or implementation has gates that affect whether
work may proceed, be reviewed, be merged, or be described as ready.

## Gate timing

| Timing | Meaning |
|---|---|
| `pre_plan` | Must be known before a plan can be trusted. |
| `pre_apply` | Must be resolved before implementation starts. |
| `during_apply` | Must be checked while implementing. |
| `pre_review` | Must be resolved before code/doc review can be meaningful. |
| `pre_ship` | Must be resolved before readiness, PR, merge, release, or user-facing completion claims. |
| `post_ship_monitor` | Accepted follow-up monitoring after a deliberately shipped change. |

## Gate status

| Status | Meaning |
|---|---|
| `passed` | Direct evidence proves the gate for the named scope. |
| `failed` | Evidence contradicts the gate. |
| `blocked` | The gate cannot run until a dependency or decision is resolved. |
| `deferred` | The user or plan explicitly moved the gate out of current scope. |
| `not_claimed` | No readiness claim is made for this gate. |
| `not_applicable` | The gate does not apply to the current work. |

`deferred` and `not_claimed` are not success states. They are honest boundaries.

## Minimum gate entry

```text
Gate: <short name>
Timing: pre_plan|pre_apply|during_apply|pre_review|pre_ship|post_ship_monitor
Applies to: <unit, file set, workflow, prompt, DB object, or release>
Status: passed|failed|blocked|deferred|not_claimed|not_applicable
Evidence: <direct evidence or "none">
Blocks: plan|implementation|review|ship|nothing
Deferral owner: <user|follow-up|not_applicable>
```

## Required gate families

Create or mention gates when any family is semantically in scope:

- evidence authenticity and claim integrity;
- prompt-contract fidelity and LLM output contracts;
- Supabase/database migration, RLS, and same-target write-read evidence;
- external side effects such as email, billing, webhooks, queues, storage, or
  trace indexing;
- browser/runtime evidence for UI or extension work;
- security, auth, privacy, or destructive operations;
- release, backup, or artifact integrity.
- CE artifact archive lifecycle, including plan/brainstorm sidecar movement,
  link integrity, and root/archive discovery boundaries.

## Skill behavior

- `ce-plan` names gates in implementation units or a plan-local
  `quality-gates.md` sidecar for broad work.
- `ce-work` verifies gates before claiming completion and reports blocked,
  deferred, and not-claimed gates plainly.
- `ce-code-review` treats missing or oversized gates as findings when they
  affect merge/readiness claims.
- `ce-commit-push-pr` must not write PR text that implies a gate passed when it
  is only deferred, blocked, or not claimed.
