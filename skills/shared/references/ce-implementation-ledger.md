# CE implementation ledger

Use this reference for broad or migration-like CE work where a task list alone
is too ephemeral to prove coverage.

## Trigger

Create a lightweight implementation ledger when work includes:

- 10 or more target files or multiple skill families;
- "review all", "update every", "migrate all", or similar exhaustive language;
- prompt/runtime contract migrations;
- database/schema/security/side-effect changes;
- broad cleanup where missed files create drift;
- explicit user request for durable progress/carry-forward evidence.

Do not create a ledger for small single-area edits.

## Default location

When executing from a plan file:

```text
docs/plans/<plan-stem>/implementation-ledger.md
```

When no plan exists, record the ledger in the smallest existing artifact that
owns the work, or state why a durable ledger was not created.

## Minimum row

```md
| ID | Target | Source class | Intended action | Status | Evidence | Notes |
|---|---|---|---|---|---|---|
| L1 | `path/or/pattern` | plan|report|repo|user|generated | create|update|verify|defer | pending|done|blocked|deferred|not_applicable | command/path/review | short note |
```

## Rules

- Source class must distinguish user/report intent from current runtime proof.
- `done` requires file or command evidence.
- `deferred` must name the future owner or gate.
- Do not store secrets, raw provider payloads, cookies, or credentials.
- The ledger is a coverage aid, not a substitute for tests or reviews.
