# CE external side-effect reality guard

Use this reference when a CE workflow creates or claims external effects beyond
local code execution.

## Side-effect classes

This guard covers:

- database writes and schema state not already fully covered by the Supabase/DB
  guard;
- storage uploads, bucket policies, and file visibility;
- queues, jobs, cron, realtime channels, and workflow status transitions;
- webhooks and third-party callbacks;
- email/SMS/push delivery;
- billing, payments, subscriptions, invoices, and entitlement changes;
- auth/session/account state;
- trace indexing, admin logs, audit logs, and observable run records.

## Core rule

A lower-level call does not prove the external effect happened.

API success, browser success, mocked jobs, local queues, generated traces, or
unit tests may be useful evidence, but they cannot prove delivery/readback from
the external system unless that leg actually ran and was observed.

## Minimum side-effect gate

```text
Side effect: <system and action>
Target environment: local|staging|production|sandbox|not_selected
Entry path: <user/API/job/workflow path>
Write evidence: <request/log/job/provider ID/path>
Readback/visibility evidence: <query, provider status, inbox, trace index, admin page>
Cleanup/rollback: <plan or not_applicable>
Claim status: passed|blocked|deferred|not_claimed
Does not prove: <stronger claims still open>
```

## Relationship to Supabase

For Supabase/Postgres/RLS/schema changes, also apply
`supabase-database-change-guard.md`. This guard is the broader layer for
non-database systems and mixed workflows where a DB write is only one step in a
larger side effect.

## Skill behavior

- `ce-plan` must plan a side-effect gate or an accepted deferral.
- `ce-work` must not claim side-effect delivery without target-environment
  evidence and readback/visibility.
- `ce-code-review` and `ce-dogfood-beta` must flag UI/API-only proof when the
  claim depends on external delivery, durable status, or observability.
