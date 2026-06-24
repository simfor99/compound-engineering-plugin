# CE completion verification

Use this reference to separate formal completion from skeptical review.

## Two different questions

1. **Verification:** Did the implementation satisfy the accepted plan,
   requirements, contracts, gates, and scope?
2. **Review:** Is the resulting system good, safe, maintainable, and sensible?

A code review can be positive while verification fails because required scope
was skipped. Verification can pass while review still finds better design.

## Verification checklist

Before claiming completion, identify the accepted source of truth:

- user request or active goal;
- requirements or brainstorm document;
- plan file and implementation units;
- prompt contracts and sidecars;
- quality gates and deferrals;
- database/side-effect/evidence guards;
- explicit non-goals.

Then check:

- every required artifact exists or has an accepted deferral;
- every required skill hook, reference, or validator named by the source is
  implemented or explicitly deferred;
- every required test or validator has run, or is reported as blocked/deferred;
- final claims do not exceed evidence-claim receipts;
- scope creep is excluded or moved to documented follow-up.

## Completion states

| State | Meaning |
|---|---|
| `verified_complete` | All required scope is done and directly evidenced. |
| `verified_with_deferrals` | Required current scope is done, but accepted deferrals remain and are not claimed as ready. |
| `not_complete` | Required scope is missing or failed. |
| `blocked` | A required gate cannot proceed without user input or external state. |

Do not use `verified_complete` when any required P0/P1 gate is only
`not_claimed`, `deferred`, or `blocked`.

## Skill behavior

- `ce-work` runs this verification before final summary.
- `lfg` runs this before commit/PR/readiness language.
- `ce-code-review` may review quality, but it does not replace this formal
  source-of-truth check.
