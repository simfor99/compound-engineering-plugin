# Document Review Output Template

Use this **exact format** when presenting synthesized review findings in Interactive mode. Findings are grouped by severity, not by reviewer.

**IMPORTANT:** Use pipe-delimited markdown tables (`| col | col |`). Do NOT use ASCII box-drawing characters.

**IMPORTANT:** Escape literal pipe characters in table cells. Any `|` that appears inside a finding's section reference, issue description, code snippet, regex pattern, or delimited-string example must be written as `\|` so column boundaries are determined only by unescaped pipes. Unescaped pipes split the cell across columns and corrupt the row's `Reviewer`, `Confidence`, and `Next step` values.

This template describes the Phase 4 interactive presentation — what the user sees before the routing question (`references/walkthrough.md`) fires. The headless-mode envelope is documented in `references/synthesis-and-presentation.md` (Phase 4 "Route Remaining Findings" section) and is separate from this template.

**User-language rule.** Render all user-facing prose, headings, table labels, routing options, preview labels, confirmations, and terminal questions in the user's conversation language. For Simon, default to German with real Umlaute and `ß`. Keep code identifiers, enum values inside hidden/internal reasoning, file paths, commands, and schema literals unchanged. Do not mix an English decision menu into a German conversation.

**CEO-guided vocabulary rule.** The user is the CEO/architect, not the implementing developer. User-facing rendered text must explain what each bucket means before asking for action. Internal enum values (`safe_auto`, `gated_auto`, `manual`, `FYI`) live in the schema and synthesis pipeline only. User-facing labels use plain language:

- `safe_auto` -> `Direkt erledigt` / `fixes`
- `gated_auto` -> `Vorgeschlagene Änderung` / `proposed fix`
- `manual` -> `Entscheidung` / `decision`
- `FYI` -> `Zur Info` / `FYI observation`

Do not show a user-facing `Tier` column with internal enum values. Replace it with a plain-language `Next step` column (`Direkt erledigt`, `Vorschlag`, `Entscheidung`, `Zur Info`) and, when useful, include the internal enum only in hidden artifacts or maintainer-facing notes.

**CEO-first point wording.** Every user-facing finding/action line must be understandable before any technical parenthesis. The first sentence answers: "What changes for me as CEO, for the plan reader, for the implementer, or for the customer/risk?" Only after that may the line add a short parenthetical for exact technical detail.

Rules:

- The `Issue` / German `Punkt` cell starts with simple outcome language, not with field names, schema terms, route names, component IDs, or implementation verbs.
- If a technical identifier is needed (`customer_job_lane`, `evidence_class`, `CB8`, route names, file names, enum values), put it after the plain-language clause in parentheses: `(technisch: ...)`.
- A line must still make sense if the parenthetical is deleted.
- Good German shape: `Jede interne Review-Karte bekommt eine klare Verbindung zu einem Kundenjob, damit Review-Arbeit nicht am Delivery-Ziel vorbeigeht (technisch: \`customer_job_lane\` je required CB-Row ergänzen).`
- Bad German shape: `customer_job_lane je required CB-Row ergänzen, damit Operator-Review-Module auf Trust-&-Delivery-Jobs einzahlen.`

**Confidence column.** The `Confidence` column shows the integer anchor value (`50`, `75`, or `100`) — never a decimal or percentage. Anchor `50` = advisory (routed to FYI); anchor `75` = verified, will hit in practice; anchor `100` = certain, evidence directly confirms. Anchors `0` and `25` are dropped by synthesis before this layer and never appear in the rendered output. Cross-persona agreement promotes by one anchor step; when this happens, the Reviewer column notes it (e.g., `coherence, feasibility (+1 anchor)`).

In user-facing German, label this column `Sicherheit` and render anchors as a phrase plus the anchor in parentheses, e.g. `sicher (100)`, `hoch (75)`, `Hinweis (50)`. Add a short legend before the first findings table whenever any actionable findings exist:

```markdown
Kurz erklärt:
- Fehler/Widerspruch: Der Plan sagt etwas, das sich beißt oder falsch wirkt.
- Lücke: Etwas Wichtiges fehlt, damit ein Entwickler sauber arbeiten kann.
- Sicherheit 100/75/50: 100 = belegt, 75 = sehr wahrscheinlich praktisch relevant, 50 = nur Hinweis.
- Nächster Schritt: Vorschlag heißt "ich kann es konkret einarbeiten"; Entscheidung heißt "du solltest die Richtung entscheiden".
```

**Routing-menu rendering.** When the platform question tool is unavailable and the agent must render a textual routing menu, use fenced lettered options (`A.`, `B.`, `C.`, `D.`). Never use Markdown ordered lists for routing or terminal menus; renderers may continue numbering from earlier report sections and change the visible option labels.

**CEO decisions required.** When synthesis marks a decision finding as `requires_ceo_decision`, render it in a distinct `CEO decisions required` subsection before the routing question. These findings are not resolved by best-judgment bulk apply or Open-Questions-only handling until the user has answered the CEO decision in chat or explicitly declined CEO handling.

## Example

```markdown
## Document Review Results

**Document:** docs/plans/2026-03-15-feat-user-auth-plan.md
**Type:** plan
**Reviewers:** coherence, feasibility, security-lens, scope-guardian
- security-lens -- plan adds public API endpoint with auth flow
- scope-guardian -- plan has 15 requirements across 3 priority levels

Applied 5 fixes. 4 items need attention (2 errors, 2 omissions). 2 FYI observations.

Kurz erklärt:
- Error: the document says something contradictory, misleading, or wrong.
- Omission: the document forgot something an implementer needs.
- Confidence 100/75/50: 100 = directly confirmed, 75 = likely to matter in practice, 50 = FYI only.
- Next step: proposed fix means the agent can show and apply a concrete edit; decision means the user should choose direction.

### Applied fixes

- Standardized "pipeline"/"workflow" terminology to "pipeline" throughout (coherence)
- Fixed cross-reference: Section 4 referenced "Section 3.2" which is actually "Section 3.1" (coherence)
- Updated unit count from "6 units" to "7 units" to match listed units (coherence)
- Added "update API rate-limit config" step to Unit 4 -- implied by Unit 3's rate-limit introduction (feasibility)
- Added auth token refresh to test scenarios -- required by Unit 2's token expiry handling (security-lens)

### P0 — Must Fix

#### Errors

| # | Section | Issue | Reviewer | Confidence | Next step |
|---|---------|-------|----------|------------|-----------|
| 1 | Requirements Trace | Goal states "offline support" but technical approach assumes persistent connectivity | coherence | 100 | Decision |

### P1 — Should Fix

#### Errors

| # | Section | Issue | Reviewer | Confidence | Next step |
|---|---------|-------|----------|------------|-----------|
| 2 | Scope Boundaries | 8 of 12 units build admin infrastructure; only 2 touch stated goal | scope-guardian | 75 | Decision |

#### Omissions

| # | Section | Issue | Reviewer | Confidence | Next step |
|---|---------|-------|----------|------------|-----------|
| 3 | Implementation Unit 3 | Plan proposes custom auth but does not mention existing Devise setup or migration path | feasibility | 100 | Proposed fix |

### P2 — Consider Fixing

#### Omissions

| # | Section | Issue | Reviewer | Confidence | Next step |
|---|---------|-------|----------|------------|-----------|
| 4 | API Design | Public webhook endpoint has no rate limiting mentioned | security-lens | 75 | Proposed fix |

### FYI Observations

Low-confidence observations surfaced without requiring a decision. Content advisory only.

| # | Section | Observation | Reviewer | Confidence |
|---|---------|-------------|----------|------------|
| 1 | Naming | Filename `plan.md` is asymmetric with command name `user-auth`; could go either way | coherence | 50 |
| 2 | Risk Analysis | Rollout-cadence decision may benefit from monitoring thresholds, though not blocking | scope-guardian | 50 |

### Residual Concerns

Residual concerns are issues the reviewers noticed but could not confirm at confidence anchor `50` or higher. These are not actionable; they appear here for transparency only and are not promoted into the review surface.

| # | Concern | Source |
|---|---------|--------|
| 1 | Migration rollback strategy not addressed for Phase 2 data changes | feasibility |

### Deferred Questions

| # | Question | Source |
|---|---------|--------|
| 1 | Should the API use versioned endpoints from launch? | feasibility, security-lens |

### CEO Decisions Required

These findings change product, architecture, governance, scope, risk, evidence,
or future working mode. They require live CEO decision in chat before
implementation-ready claims.

| # | Section | Decision | Reviewer | Confidence |
|---|---------|----------|----------|------------|
| 1 | Scope Boundaries | Decide whether the adoption handoff is part of this slice or follow-up governance | product-lens | 75 |

### Coverage

| Persona | Status | Findings | Direct fixes | Proposed fixes | Decisions | FYI | Residual |
|---------|--------|----------|--------------|----------------|-----------|-----|----------|
| coherence | completed | 5 | 3 | 0 | 1 | 1 | 0 |
| feasibility | completed | 3 | 1 | 1 | 0 | 0 | 1 |
| security-lens | completed | 2 | 1 | 1 | 0 | 0 | 0 |
| scope-guardian | completed | 2 | 0 | 0 | 1 | 1 | 0 |
| product-lens | not activated | -- | -- | -- | -- | -- | -- |
| design-lens | not activated | -- | -- | -- | -- | -- | -- |

Dropped: 3 (anchors 0/25 suppressed)
Context FYI: 2 (true but not actionable for current target context)
Subtracted: 1 (context-mismatched or overbuilt findings suppressed)
Simplified: 1 (suggested fixes trimmed to smallest adequate fix)
Chains: 1 root with 2 dependents
Restated: 2 (residual/deferred items suppressed as duplicates of actionable findings)
```

## Section Rules

- **Summary line**: Always present after the reviewer list. Format in the user's language. In German: "Direkt erledigt: N. Braucht Aufmerksamkeit: K (X Fehler/Widersprüche, Y Lücken). Zur Info: Z." Omit any zero clause except the FYI clause when zero (it's informative that none surfaced).
- **Applied fixes**: List all fixes that were applied automatically (`safe_auto` tier). Include enough detail per fix to convey the substance — especially for fixes that add content or touch document meaning. Omit section if none.
- **P0-P3 sections**: Only include sections that have actionable findings (`gated_auto` or `manual`). Omit empty severity levels. Within each severity, separate into Errors and Omissions in the user's language (`Fehler/Widersprüche` and `Lücken` in German). Omit a sub-header if that severity has none of that type. The `Issue` / German `Punkt` cell follows CEO-first point wording: simple consequence first, optional technical parenthetical second. The `Next step` column surfaces whether a finding has a concrete proposed fix or requires user judgment. Do not show internal tier names in user-facing tables.
- **FYI Observations**: Findings at confidence anchor `50` regardless of `autofix_class`. Surface here for transparency; these are not actionable and do not enter the walk-through. Omit section if none.
- **Residual Concerns**: Residual concerns noted by personas that did not make it above the confidence gate. Listed for transparency; not promoted into the review surface (cross-persona agreement boost runs on findings that already survived the gate, per synthesis step 3.4). Omit section if none.
- **Deferred Questions**: Questions for later workflow stages. Omit if none.
- **CEO Decisions Required**: Findings marked `requires_ceo_decision`. Render after Deferred Questions and before Coverage. Omit if none. These findings remain visible in the normal severity tables as decisions, but this subsection is the explicit handoff to the chat CEO-decision flow.
- **Compact rendering for FYI / Residual / Deferred (high-count mode)**: When the combined count across these three sections is **5 or more**, collapse each section to a one-line summary followed by the items as a tight bullet list (no table, no per-item `Why` elaboration). Rationale: these sections are observational, not decision-forcing — when they are lengthy, they bury the actionable tiers above them. A P0/P1/P2 actionable finding stays fully rendered regardless of how many FYI/Residual/Deferred items exist. When the combined count is 4 or fewer, render each section as today.
- **Coverage**: Always include. All counts are **post-synthesis**. **Findings** must equal Direct fixes + Proposed fixes + Decisions + FYI exactly — if deduplication merged a finding across personas, attribute it to the persona with the highest confidence anchor and reduce the other persona's count. **Residual** = count of `residual_risks` from this persona's raw output (not the promoted subset in the Residual Concerns section). The `Direct fixes` column counts `safe_auto` findings at anchor `100`, `Proposed fixes` counts `gated_auto` findings at anchor `75` or `100`, `Decisions` counts `manual` findings at anchor `75` or `100`, and `FYI` counts findings at anchor `50` regardless of `autofix_class`. Findings at anchors `0` or `25` were dropped by synthesis and do not appear in any column. Do NOT invent internal/debug columns (e.g., `Dropped`, `Surviving`) in user-facing output.
- **Coverage footnote lines** (optional, appear below the table when non-zero): `Context FYI: N (true but not actionable for current target context)`, `Subtracted: N (context-mismatched or overbuilt findings suppressed)`, and `Simplified: N (suggested fixes trimmed to smallest adequate fix)` when synthesis 3.1b changed finding routing. `Dropped: N (anchors 0/25 suppressed)` when synthesis 3.2 dropped any findings. `Chains: N root(s) with M dependents` when premise-dependency chains exist. `Restated: N (residual/deferred items suppressed as duplicates of actionable findings)` when synthesis 3.9 suppressed any restatements. These footnotes — not the summary line, not per-persona columns — are the canonical location for cross-cutting counts that don't fit the per-persona shape. Order: `Context FYI:`, then `Subtracted:`, then `Simplified:`, then `Dropped:`, then `Chains:`, then `Restated:`, each on its own line. Omit any footnote whose count is zero.

## Chain-Rendering Rules

Premise-dependency chains from synthesis step 3.5c annotate roots and dependents. Rendering follows the same count invariant documented in the synthesis reference; this template restates the rules so interactive output cannot drift from the headless envelope.

- **Dependents render only under their root.** When a finding has `dependents`, render the root at its normal severity position (in its P-tier Errors or Omissions table). Immediately below the root's table row, emit an indented `Dependents (N)` sub-block listing each dependent's `# | Section | Issue | Reviewer | Confidence | Next step` entry. Dependents MUST NOT appear at their own severity position. Findings without `depends_on` and without `dependents` render as they do today.
- **Count invariant.** The `Findings` column in Coverage continues to equal Direct fixes + Proposed fixes + Decisions + FYI. Each finding counts exactly once: a dependent counts in its assigned bucket (`Direct fixes` / `Proposed fixes` / `Decisions` / `FYI`) but does NOT render at its own severity position. The source of truth is the post-Step-4 `dependents` array on each root — the same array the headless envelope reads — so coverage count and rendering cannot drift.
- **Chains line (optional).** When one or more chains exist, add a final line to the coverage block: `Chains: N root(s) with M dependents` where N is the number of roots and M is the total dependent count summed across all roots. Omit the line when no chains exist. This mirrors the `Chains:` line the headless envelope emits in `references/synthesis-and-presentation.md` so reviewers get the same chain visibility in both modes.
