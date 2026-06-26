# CE artifact archive lifecycle

Use this reference when CE skills create, discover, archive, review, or reopen
planning artifacts under `docs/plans/` or `docs/brainstorms/`.

## Lifecycle contract

Directory location is the lifecycle signal:

- Active roots:
  - `docs/plans/` contains plans that are open, not yet implemented, or
    intentionally still active.
  - `docs/brainstorms/` contains requirements, review logs, and working notes
    that are open or still part of active planning.
- Archive roots:
  - `docs/plans/_archive/` contains completed/read-only historical plans.
  - `docs/brainstorms/_archive/` contains completed/read-only brainstorm
    artifacts whose decisions are represented downstream.

Do not add a mutable `status:` lifecycle field to CE artifacts. The artifact
body remains a decision or discovery record; lifecycle is represented by
location plus git history and archive ledgers.

## Discovery rules

Auto-discovery means a blank invocation, "latest", "open", branch-keyword
matching, or any inferred current-work search.

- Auto-discovery reads active roots only.
- Auto-discovery must ignore `_archive` subtrees.
- Explicit paths may point to active roots or `_archive` paths.
- Explicit origin links, PR-body links, issue links, and user-named files may
  resolve archived artifacts when the path exists.
- If an inferred search has no active match, do not silently fall back to the
  archive unless the workflow explicitly says it is looking for history.

## Plan sidecars

A same-stem plan sidecar directory moves with its plan file:

```text
docs/plans/<plan-stem>.md
docs/plans/<plan-stem>/
docs/plans/_archive/<plan-stem>.md
docs/plans/_archive/<plan-stem>/
```

The sidecar can contain `evidence-receipt.md`, `implementation-ledger.md`,
`quality-gates.md`, `prompts/`, `prompt-contracts/`, screenshots, traces, or
other plan-owned evidence. Moving only the plan file is incomplete.

## Brainstorm artifact families

Use `brainstorm_artifact_family_key` when deciding which brainstorm artifacts
move together after planning.

`brainstorm_artifact_family_key` is the basename after stripping exactly one
known terminal suffix:

- `-requirements`
- `-working-notes`
- `-review-log`

Examples:

- `2026-06-23-url-admission-beta-ux-requirements.md` ->
  `2026-06-23-url-admission-beta-ux`
- `2026-06-23-url-admission-beta-ux-working-notes.md` ->
  `2026-06-23-url-admission-beta-ux`

Files share a brainstorm family only when the resulting date/topic key is
identical. Topic-adjacent files outside that exact family need an explicit
backlink, migration-ledger review, or Simon confirmation before archival.

## Archive timing

`ce-plan` archives brainstorm artifacts only after a plan is successfully
written and the origin requirements are represented by that plan.

- Archive the explicit upstream origin requirements document.
- Archive directly linked files in the same deterministic
  `brainstorm_artifact_family_key`.
- Preserve links by leaving plan `origin:` values repo-relative to the final
  artifact path, or by updating them during the same archive pass.

`ce-work` archives plans only after required checks pass.

- The plan completion gate ledger is produced or updated.
- Required verification gates have passed or are honestly marked blocked,
  deferred, or not claimed.
- The evidence receipt exists when the plan requires one.
- Same-stem sidecars are ready to move with the plan.
- Link integrity has been checked.
- The final response can report the archived path.

## Archive ledgers

Archive, migration, and reopen decisions must be written to one canonical
ledger for the acting plan or migration run.

- Plan archival by `ce-work`: write to the plan's same-stem sidecar ledger,
  `docs/plans/<plan-stem>/archive-lifecycle-ledger.md`, before the sidecar is
  moved. After archival, that ledger lives at
  `docs/plans/_archive/<plan-stem>/archive-lifecycle-ledger.md` with the rest
  of the sidecar.
- Brainstorm-origin archival by `ce-plan`: write to the generated plan's
  same-stem sidecar ledger, `docs/plans/<plan-stem>/archive-lifecycle-ledger.md`.
- Historical cleanup or bulk migration: write to the executing migration
  plan's same-stem sidecar ledger. When no plan context exists, create an
  explicit dated migration plan first; do not scatter lifecycle decisions across
  ad hoc files.
- Reopening an archived plan: append the row to the plan's sidecar ledger after
  the sidecar has been restored to `docs/plans/<plan-stem>/`.

Minimum row shape:

| date | action | source_path | target_path | state | confirmation_source | reason |
|---|---|---|---|---|---|---|

Use `state` values from the migration ledger section below:
`active_open`, `archived_completed`, or `requires_simon_decision`.

## Reopening

Archived work is read-only history by default. Reopen only when the user
explicitly requests it and confirms the move.

Reopening moves the artifact and same-stem sidecar bundle back to the active
root and records a row in `docs/plans/<plan-stem>/archive-lifecycle-ledger.md`
with:

- archived source path;
- restored active path;
- reason for reopening;
- confirmation source;
- date of the move.

Do not reopen automatically because an inferred search matched an archived
artifact.

## Migration ledger

Historical cleanup must classify every current root artifact before claiming
active roots are clean.

Allowed states:

- `active_open`: no durable completion evidence exists, or the artifact still
  represents open work.
- `archived_completed`: durable completion evidence exists and the artifact plus
  sidecar can move safely.
- `requires_simon_decision`: evidence conflicts, only stale `status:` exists,
  sidecar/origin evidence is weak, or family matching is not deterministic.

`requires_simon_decision` blocks any claim that `docs/plans/` or
`docs/brainstorms/` contains only open work.

## Evidence language

Use evidence classes from `evidence-authenticity-guard.md`.

- Static text scans prove contract wording only.
- Local filesystem movement proves local archive mechanics only.
- A clean root listing proves local tree state only.
- None of the above proves product runtime, provider behavior, browser
  behavior, Supabase persistence, or production readiness.
