# CE Supabase and database change guard

This reference is the routing and safety guard for Compound Engineering work
that touches Supabase, Postgres, durable persistence, database migrations,
storage, auth/RLS, queues, cron, realtime, or trace/status indexing. It adapts
external side-effect reality principles to CE plans, work, reviews, debugging,
and hands-off pipelines.

## Default posture

Treat database state as an external side effect, not as code-local behavior.

Local migration files, generated types, unit tests, mocked API responses,
browser success, trace artifacts, and fixture replay are useful partial
evidence. They do not prove that the target database contains the expected
schema, rows, policies, status, or downstream-readable state.

Do not claim Supabase, Postgres, persistence, auth/RLS, storage, queue, trace
indexing, or status-write readiness unless one of these is true:

- same-target write-read evidence exists;
- the work is explicitly limited to planning/design/review;
- an accepted deferral records owner, risk, target environment, and follow-up.

An accepted deferral never counts as readiness. It only permits the honest
status `blocked`, `deferred`, or `not_claimed` while preserving who owns the
unproven database side effect.

## Trigger conditions

Load this guard when a CE skill sees any of these terms or semantic equivalents:

- Supabase, Postgres, database, DB, SQL, table, column, index, view, trigger,
  function, policy, RLS, row-level security, schema, migration, backfill;
- Supabase Auth, sessions, JWT, `auth.uid()`, service role, anon/authenticated
  roles, user metadata, app metadata;
- Supabase Storage, buckets, realtime, cron, queues, vectors, Edge Functions;
- durable workflow/status writes, trace indexing, admin review persistence,
  audit logs, code redemption logs, abuse/security logs;
- any claim that production, staging, remote Supabase, or local Supabase now
  contains or should contain new durable state, including production/staging
  database state.

If the work merely reads a type name that happens to include "database" but
does not touch persistence, state that the guard is `not_applicable`.

## Source hierarchy

Follow higher-priority repo and platform instructions first. This guard adds a
CE-specific routing contract; it does not replace:

1. active project instructions such as `AGENTS.md`, `CLAUDE.md`, or equivalent;
2. repo migration governance when present, for example
   `docs/planning/ACTIVE_MIGRATIONS.md`;
3. the active Supabase skill when available (`supabase`);
4. OpenSpec or repo-specific external side-effect gates when the active workflow
   explicitly provides them.

## Planning contract

CE brainstorm and CE plan must not turn database work into an implicit
implementation detail. When this guard is triggered, requirements or plans must
name a database gate or an accepted deferral.

For each DB/Supabase unit, include:

- target environment class: `local_supabase`, `remote_supabase`, `staging`,
  `production`, or `not_yet_selected`;
- target project/schema identity when known;
- migration path and migration creation method;
- affected tables, columns, views, functions, policies, buckets, queues, or
  auth metadata;
- RLS and role-access stance for exposed schemas;
- role-specific access proof plan when policies matter: `anon`,
  `authenticated user A`, `authenticated user B`, and `service_role/admin`
  where relevant, including both allowed and denied access checks;
- real entry path that causes writes, not only direct SQL or service calls;
- expected row/object identifiers and minimum field assertions;
- success/error/status fields to check;
- downstream reload/reference proof when another stage or surface consumes the
  persisted state;
- cleanup or retention stance for test data;
- verification commands or evidence package shape.

If the plan is intentionally pre-DB, say so explicitly and list what later
feedback decides before migrations are designed.

## Supabase implementation rules

Before schema or policy work:

- read repo migration governance such as `docs/planning/ACTIVE_MIGRATIONS.md`
  when present;
- inspect existing structure with available Supabase tools, CLI, SQL, or repo
  migrations before designing new tables;
- check current Supabase documentation or the Supabase skill for changed CLI,
  RLS, auth, and migration behavior when the task depends on current behavior;
- do not invent migration filenames; use the repo's migration tool. For
  hand-written Supabase CLI migrations, create the file with
  `supabase migration new <descriptive_name>` unless repo instructions specify
  another generator. For local schema iteration, follow the current Supabase
  skill/docs: iterate against the intended local target with `execute_sql`,
  `supabase db query`, or repo tooling as appropriate, then generate a clean
  migration with the documented diff/pull flow such as
  `supabase db pull <descriptive-name> --local --yes` when that is the active
  project convention. Check `supabase --help` and command-specific `--help`
  before relying on CLI syntax;
- do not use direct remote writes, MCP `apply_migration`, or destructive SQL
  against remote/staging/production without explicit current user approval and
  a named target environment;
- run advisors/log checks where available before treating security-sensitive
  schema, policy, function, storage, or auth changes as ready.

Security defaults:

- enable RLS on tables in exposed schemas, including `public`, unless a
  documented internal-only schema/access model explains why not;
- prove RLS and policy behavior with the relevant Supabase role/JWT/client
  shape, not only with `service_role` or a direct SQL superuser. For
  tenant-/owner-scoped data, include positive and negative checks such as
  `authenticated user A can read own row`, `authenticated user B cannot read
  user A's row`, `anon cannot access protected data`, and `service_role/admin`
  can perform the intended administrative path;
- do not use `user_metadata` for authorization decisions; use trusted app
  metadata or database-owned authorization data;
- do not expose service-role or secret keys to public clients;
- treat server-side `service_role` as an RLS-bypassing admin capability, not as
  proof that user-scoped access works. Use it only for explicit admin/system
  paths with a preceding server-side authorization or ownership check. For
  user-driven reads/writes, prefer evidence through the user's JWT/RLS path and
  flag unexplained `service_role` use in user-scoped flows as a security risk;
- for exposed views, use `security_invoker = true` where applicable or keep the
  view out of exposed schemas/roles; do not assume a view inherits table RLS;
- avoid `SECURITY DEFINER`; when truly required, place it outside exposed
  schemas where possible, add explicit authorization checks, lock down grants,
  review `EXECUTE` grants, and verify with advisors;
- do not use `auth.role()` in new policies; prefer policy `TO` clauses and
  ownership predicates such as `auth.uid()` where row ownership matters;
- policies for `UPDATE` usually need both `USING` and `WITH CHECK`; `TO
  authenticated` alone is not authorization.

## Evidence contract

Use the weakest honest claim:

| Evidence | May prove | Does not prove |
|---|---|---|
| Migration file exists | Intended schema change is represented locally. | Migration applied to the target DB. |
| Generated types changed | Codegen saw some schema state. | Runtime target has the schema or RLS works. |
| Unit test with mocked DB | Service logic around a DB adapter. | Real table, policy, trigger, or persistence behavior. |
| API/browser success | Entry path responded. | Durable DB state unless followed by same-target query. |
| Trace artifact | Runtime recorded something. | Remote trace index or persisted business rows. |
| Same-target write-read query | Target DB contains expected rows/fields/status. | Untested tenants, policies, cleanup, or downstream use. |

For database persistence, a passing readiness claim needs:

- target environment/project/schema identity;
- entry path used to create/update state;
- run/workflow/request/user/code IDs;
- schema/column/policy/object existence proof in the same target;
- row-level query proof for expected tables and fields;
- role-specific RLS/access proof for the actual roles and JWT/client shapes in
  use, including positive and negative checks where policies matter;
- success/error/status field proof;
- downstream consumer reload/reference proof if the rows are consumed later;
- cleanup/retention stance for durable test data.

## Review contract

CE code review and document review must flag:

- migration or persistence work without a same-target evidence gate;
- plans that treat a migration file, API response, browser flow, or unit test as
  DB-readiness proof;
- missing RLS/role/access stance on exposed Supabase tables;
- public-client service-role exposure or auth based on user-editable metadata;
- server-side `service_role` use in user-scoped flows without explicit
  authorization/ownership checks and a reason to bypass RLS;
- destructive DDL, backfills, NOT NULL constraints, drops/renames, or policy
  changes without deploy-window/rollback/verification notes;
- remote Supabase claims without target project/schema identity.
- accepted deferrals that are presented as passed readiness instead of
  `blocked`, `deferred`, or `not_claimed`.

## Reporting receipt

Triggered CE work should include a compact receipt:

```text
Supabase/DB Guard: loaded|not_applicable
Target environment: local_supabase|remote_supabase|staging|production|not_yet_selected
Migration governance loaded: yes|no|not_found|not_applicable
Supabase docs/skill loaded: yes|no|not_applicable
Schema/RLS evidence: same_target_write_read|local_only|mock_only|deferred|not_claimed
External side-effect readiness: passed|blocked|deferred|not_claimed
Unproven: [...]
```

## Non-goals

This guard does not:

- replace the Supabase skill or official Supabase documentation;
- authorize remote mutations by itself;
- require a database migration for every product idea;
- make DB work heavier than needed when the current phase is explicitly
  pre-persistence;
- let CE bypass OpenSpec external side-effect gates when the active workflow is
  OpenSpec.
