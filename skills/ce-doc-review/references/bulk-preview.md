# Bulk Action Preview

This reference defines the compact proposal preview that Interactive mode shows before every bulk action — best-judgment / proposal-package routing option B, Append-to-Open-Questions routing option C, and the walk-through's "proposal package for the rest" option D. The preview gives the user a single-screen view of what the agent is about to do, with exactly two options to proceed or cancel. The preview is a transparency gate: no document edit or Open-Questions append happens before the user confirms it.

Interactive mode only.

---

## When the preview fires

Three call sites:

1. **Routing option B (top-level proposal package)** — after the user picks `Show my proposed resolution package — no edits until you confirm the preview` from the routing question, but before any action executes. Scope: every pending non-CEO `gated_auto` or `manual` finding at confidence anchor `75` or `100`.
2. **Routing option C (top-level Open-Questions-only record)** — after the user picks `Record as Open Questions only — no direct fixes, no implementation decision` but before any append runs. Scope: every pending non-CEO `gated_auto` or `manual` finding at confidence anchor `75` or `100`. Every finding appears under `Recording as Open Questions (N):` regardless of the agent's natural recommendation, because option C is batch-defer. CEO-required findings are excluded and must be handled through the CEO decision gate or explicitly declined by the user.
3. **Walk-through proposal package for the rest** — after the user picks `Show a proposed resolution package for the rest` from a per-finding question, but before the remaining findings are resolved. Scope: the current finding and everything not yet decided, excluding CEO-required findings. Already-decided findings from the walk-through are not included in the preview.

In all three cases the user confirms with `Proceed` or backs out with `Cancel`. No per-item decisions inside the preview — per-item decisioning is the walk-through's role.

---

## Preview structure

The preview is grouped by the action the agent intends to take. Bucket headers appear only when their bucket is non-empty.

```
<Path label> — <scope summary>:

Nothing has been changed yet. If you confirm, I will do exactly this:

Applying directly (N):
  [P0] <section> — <plain-language concrete effect> (technically: <optional exact detail>)
  [P1] <section> — <plain-language concrete effect> (technically: <optional exact detail>)

Recording as Open Questions (N):
  [P2] <section> — <plain-language decision or uncertainty being parked> (technically: <optional exact detail>)

Skipping (N):
  [P2] <section> — <plain-language reason no action is useful now> (technically: <optional exact detail>)

CEO decisions still needed (N):
  [P1] <section> — <one-line consequence; will be asked in chat>
```

Worked example for routing option B (top-level best-judgment):

```
Proposed resolution package — 8 findings:

Nothing has been changed yet. If you confirm, I will do exactly this:

Applying directly (4):
  [P0] Requirements Trace — Readers can follow the requirement without hitting a wrong reference (technically: renumber R4 to match the unit reference)
  [P1] Unit 3 Files — The implementation has a clear fallback if the report file was already renamed (technically: add read-fallback for the renamed file)
  [P2] Key Technical Decisions — The plan uses the framework's built-in deprecation path instead of inventing a custom one (technically: use the framework's Deprecated field)
  [P3] Overview — The summary count matches the actual list, so scope is not inflated (technically: correct 6 to 5)

Recording as Open Questions (2):
  [P2] Scope Boundaries — The plan records that merging Unit 2 and Unit 3 is still a real scope decision
  [P2] Risks — The plan records the concern that alias support may look safer than it really is

Skipping (2):
  [P2] Miscellaneous Notes — No change, because this is only a weak style preference
  [P3] Abstraction Commentary — No change, because the concern is speculative and subjective
```

---

## Scope summary wording by path

- **Routing option B (top-level proposal package):** header reads `Proposed resolution package — N findings:`. In German: `Mein Vorschlagspaket — N Punkte:`.
- **Routing option C (top-level Open-Questions-only record):** header reads `Open-Questions record package — N findings:`. In German: `Nur als offene Fragen notieren — N Punkte:`. Every non-CEO finding lands in the `Recording as Open Questions (N):` bucket.
- **Walk-through proposal package for the rest:** header reads `Proposed resolution package — N remaining findings (K already decided):`. In German: `Mein Vorschlagspaket — N verbleibende Punkte (K schon entschieden):`. Already-decided findings from the walk-through are not included in the preview or in the bucket counts. The `K already decided` counter communicates that the walk-through was partially completed.

---

## Per-finding line format

Each line uses **CEO-first point wording**. It must first say in simple language what will happen if the user confirms the package, then optionally include exact technical detail in parentheses. The line is not a raw `suggested_fix` dump and is not copied mechanically from the first sentence of `why_it_matters`.

- **Shape:** `[<severity>] <section> — <plain-language concrete effect> (technically: <optional exact detail>)`
- **German shape:** `[<severity>] <section> — <einfache Wirkung für Plan, Umsetzung, Kunde oder Risiko> (technisch: <optionales Detail>)`
- **Apply bucket:** derive the first clause from what the `suggested_fix` achieves, not from its syntax. Example: `Jede interne Review-Karte bekommt eine klare Verbindung zu einem Kundenjob, damit Review-Arbeit nicht am Delivery-Ziel vorbeigeht (technisch: \`customer_job_lane\` je required CB-Row ergänzen).`
- **Open-Questions bucket:** first clause names the decision or uncertainty being parked, not the implementation detail. Example: `Die offene Frage wird festgehalten, ob dieser Schutz jetzt nötig ist oder bewusst später kommt (technisch: Guard-Vertrag für Proof-Routen).`
- **Skip bucket:** first clause names why no action is useful now. Example: `Keine Änderung, weil der Plan diesen Punkt an anderer Stelle bereits ausreichend regelt.`
- **Technical parenthetical:** use it only when exact identifiers help implementation. Keep it short. If the line contains a technical identifier, schema field, code name, route, file path, enum value, or component ID, the identifier belongs in the parenthetical, not as the opening phrase.
- **Deletability test:** the line must remain understandable if the parenthetical is deleted.
- **Width target:** prefer 100-140 characters over cryptic compression. Do not truncate away the CEO-level clause; if space is tight, omit the technical parenthetical first.
- **No section numbering** unless the reader needs it to locate the issue (when multiple findings hit the same named section).

When `suggested_fix` or `why_it_matters` is missing, still render a CEO-first paraphrase from the finding title and section; then note the data gap in the completion report's Coverage section if it affects more than a few findings in the same run.

---

## Question and options

After the preview body is rendered, ask the user using the platform's blocking question tool (`AskUserQuestion` in Claude Code, `request_user_input` in Codex, `ask_question` in Antigravity CLI (`agy`), `ask_user` in Pi (requires the `pi-ask-user` extension)). In Claude Code, the tool should already be loaded from the Interactive-mode pre-load step — if it isn't, call `ToolSearch` with query `select:AskUserQuestion` now. The text fallback below applies only when the harness genuinely lacks a blocking tool — `ToolSearch` returns no match, the tool call explicitly fails, or the runtime mode does not expose it (e.g., Codex edit modes without `request_user_input`). A pending schema load is not a fallback trigger. Never silently skip the question.

Stem (adapted to the path):

- For routing B: `If you confirm, I will apply the package above exactly as shown. Proceed?`
- For routing C: `If you confirm, I will record the findings above as Open Questions only. Proceed?`
- For walk-through proposal package for the rest: `If you confirm, I will resolve the remaining findings above exactly as shown. Proceed?`

German stems:

- Routing B: `Wenn du bestätigst, setze ich das Paket oben genau so um. Fortfahren?`
- Routing C: `Wenn du bestätigst, notiere ich die Punkte oben nur als offene Fragen. Fortfahren?`
- Walk-through rest package: `Wenn du bestätigst, löse ich die verbleibenden Punkte oben genau so auf. Fortfahren?`

Options (exactly two, in all three cases):

- `Proceed` — execute the package as shown
- `Cancel` — change nothing, return to the originating question

German labels: `Fortfahren — genau dieses Paket umsetzen` and `Abbrechen — nichts ändern`.

Only when `ToolSearch` explicitly returns no match or the tool call errors — or on a platform with no blocking question tool — fall back to presenting the two options as a fenced lettered option block and waiting for the user's next reply. Do not use Markdown ordered lists for this fallback; render `A. Proceed` and `B. Cancel` so prior numbered report sections cannot change the visible option labels.

---

## Cancel semantics

- **From routing option B Cancel:** return the user to the routing question (the four-option menu). Do not edit the document, do not append any Open Questions entries, do not record any state.
- **From routing option C Cancel:** same — return to the routing question, no side effects.
- **From walk-through proposal-package Cancel:** return the user to the current finding's per-finding question (not to the routing question). The walk-through continues from where it was, with prior decisions intact.

In every case, `Cancel` changes no on-disk or in-memory state.

---

## Proceed semantics

When the user picks `Proceed`:

- **Routing option B (top-level proposal package):** for each non-CEO finding in the package, execute the recommended action. Apply findings go into the Apply set for a single end-of-batch document-edit pass (see `walkthrough.md` for the Apply batching rules). Defer findings route through `references/open-questions-defer.md`. Skip findings are recorded as no-action. CEO-required findings are not executed here. After all actions complete, emit the unified completion report (see `walkthrough.md`).
- **Routing option C (top-level Open-Questions-only record):** every non-CEO finding routes through `references/open-questions-defer.md` for Open Questions append. No document edits apply (beyond the Open Questions section additions themselves). CEO-required findings are not appended as a substitute for the live CEO decision. After all appends complete (or fail), emit the unified completion report.
- **Walk-through proposal package for the rest:** same as routing option B, but scoped to the findings the user hadn't decided on. Apply findings join the in-memory Apply set with the ones the user already picked during the walk-through; all dispatch together in the single end-of-walk-through Apply pass.

Failure during `Proceed` (e.g., an Open Questions append fails for one finding during a batch Defer) follows the failure path defined in `references/open-questions-defer.md` — surface the failure inline with Retry / Fall back / Convert to Skip, continue with the rest of the plan, and capture the failure in the completion report's failure section.

---

## Edge cases

- **Zero findings in a bucket:** omit the bucket header. A preview with only Apply and Skip does not show an empty `Appending to Open Questions (0):` line.
- **All findings in one bucket:** preview still shows the bucket header; Proceed / Cancel still offered. This is the common case for routing option C (every finding under `Appending to Open Questions`).
- **N=1 preview (only one finding in scope):** the preview still uses the grouped format, just with a single-line bucket. `Proceed` / `Cancel` still apply.
- **Open Questions append unavailable** (document is read-only, append flow reports no-go): routing option C is not offered upstream (see `references/open-questions-defer.md` unavailability handling). Best-judgment / proposal-package option B and walk-through proposal-package-for-the-rest can still run — they may contain per-finding Defer recommendations from synthesis. Before rendering any proposal-package preview, downgrade every Defer recommendation to Skip when the session's cached append-availability is false, and surface the downgrade on the preview itself (e.g., a `Skipping — append unavailable (N):` bucket, or a note in the header: `N Defer recommendations downgraded to Skip — document is read-only.`).
- **Walk-through proposal package with zero remaining findings:** the walk-through's own logic suppresses the proposal-package option when N=1 and otherwise, so the preview should never be invoked with zero remaining findings. If it is, render `Proposed resolution package — 0 remaining findings` and fall through to Proceed with no-op.
