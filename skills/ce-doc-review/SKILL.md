---
name: ce-doc-review
description: Review requirements or plan documents using parallel persona agents that surface role-specific issues. Use when a requirements document or plan document exists and the user wants to improve it.
argument-hint: "[mode:headless] [path/to/document.md]"
---

# Document Review

Review requirements or plan documents through multi-persona analysis. Dispatches generic subagents seeded with skill-local reviewer prompt assets, applies only unambiguous direct fixes, and routes remaining findings through a CEO-guided interaction: guided walk-through, transparent proposal package, Open-Questions-only record, or report-only. User-facing output must be in the user's conversation language and must explain internal review buckets in plain language before asking for decisions. **CEO-first point wording:** every user-visible finding/action line must first say, in simple CEO-level language, what concretely changes for the reader, implementer, customer, or risk posture; technical field names, IDs, schema terms, route names, or implementation details may appear only afterward in a short parenthetical such as `(technically: ...)` / `(technisch: ...)`.

## Interactive mode rules

- **Pre-load the platform question tool before any question fires.** In Claude Code, `AskUserQuestion` is a deferred tool — its schema is not available at session start. At the start of Interactive-mode work (before the routing question, per-finding walk-through questions, bulk-preview Proceed/Cancel, and Phase 5 terminal question), call `ToolSearch` with query `select:AskUserQuestion` to load the schema. Load it once, eagerly, at the top of the Interactive flow — do not wait for the first question site. On Codex, Gemini, and Pi this preload is not required.
- **The lettered-option fallback applies only when the harness genuinely lacks a blocking question tool** — `ToolSearch` returns no match, the tool call explicitly fails, or the runtime mode does not expose it (e.g., Codex edit modes where `request_user_input` is unavailable). A pending schema load is not a fallback trigger; call `ToolSearch` first per the pre-load rule. In genuine-fallback cases, present options as stable letter labels (`A.`, `B.`, `C.`, `D.`) inside a fenced code block and wait for the user's reply — never use Markdown ordered lists for routing menus, because renderers may continue previous numbering and change the visible option numbers. Rendering a question as narrative text because the tool feels inconvenient, because the model is in report-formatting mode, or because the instruction was buried in a long skill is a bug. A question that calls for a user decision must either fire the tool or fall back loudly.

## Phase 0: Detect Mode

Check the skill arguments for `mode:headless`. Arguments may contain a document path, `mode:headless`, or both. Tokens starting with `mode:` are flags, not file paths — strip them from the arguments and use the remaining token (if any) as the document path for Phase 1.

If `mode:headless` is present, set **headless mode** for the rest of the workflow.

**Headless mode** changes the interaction model, not the classification boundaries. ce-doc-review still applies the same judgment about which tier each finding belongs in. The only difference is how non-safe_auto findings are delivered:

- `safe_auto` fixes are applied silently (same as interactive)
- `gated_auto`, `manual`, and FYI findings are returned as structured text for the caller to handle — no blocking-question prompts, no interactive routing
- Phase 5 returns immediately with "Review complete" (no routing question, no terminal question)

The caller receives findings with their original classifications intact and decides what to do with them.

Callers invoke headless mode by including `mode:headless` in the skill arguments, e.g.:

```
Skill("ce-doc-review", "mode:headless docs/plans/my-plan.md")
```

If `mode:headless` is not present, the skill runs in its default interactive mode with the routing question, walk-through, and bulk-preview behaviors documented in `references/walkthrough.md` and `references/bulk-preview.md`.

## Phase 1: Get and Analyze Document

**If a document path is provided:** Read it, then proceed.

If the document contains product/runtime prompts, System Prompt, User Prompt,
output JSON, structured LLM output, provider requests, rendered prompts,
workflow stages, model-visible data, prompt files, or concrete prompt
contracts, read `../shared/references/ce-runtime-prompt-contract-guard.md`
before selecting personas. Pass prompt-contract concerns into the review brief:
source class separation, repo profile presence, exactness/write-back rules,
runtime/provider-request transport, output validation, and evidence class.

If the document contains Supabase, Postgres, SQL, database tables, columns,
indexes, views, triggers, functions, schemas, migrations, RLS, policies,
`auth.uid()`, auth/session persistence, storage buckets or policies, queues,
cron, realtime, vectors, `service_role`, backfills, trace indexing, durable
status writes, admin logs, audit logs, code-redemption persistence, or
production/staging database state, read
`../shared/references/supabase-database-change-guard.md` before selecting
personas. Pass database side-effect concerns into the review brief: target
environment, migration governance, affected objects, RLS/access stance, real
entry path, same-target write-read evidence, cleanup/retention, downstream
reload/reference proof, and accepted deferrals.

Build one `{active_guard_brief}` for the subagent template. If no shared guard
triggered, set it to `Active guard brief: none`. If the Supabase/DB guard
triggered, include a concise block headed `Active Supabase/DB guard:` with the
target/evidence concerns and a reminder that migration files, generated types,
API/browser success, traces, mocks, and replays are partial evidence only. If
the runtime prompt-contract guard triggered too, include its prompt-contract
concerns in the same active guard brief.

If the document contains material product, architecture, governance, risk,
security, cost, release, data-flow, prompt/runtime, evidence, or scope
uncertainty, read `../shared/references/decision-assumption-ledger.md` before
selecting personas and pass hidden-assumption concerns into the active guard
brief. If the document contains P0/P1 source commitments, exact user decisions,
must-survive facts, non-goals, or transfer/migration report items, read
`../shared/references/source-coverage-matrix.md`. If it contains broad
file/skill coverage or "update all" style work, read
`../shared/references/ce-implementation-ledger.md`. If it contains readiness,
workflow, persistence, provider, browser, trace, external side-effect, or ship
claims, read `../shared/references/evidence-claim-integrity-guard.md`,
`../shared/references/external-side-effect-reality-guard.md`, and
`../shared/references/ce-quality-gates.md` as applicable.
If the document contains a case matrix, UX matrix, acceptance examples, state
machine, decision matrix, LLM/provider classification, scraper-driven behavior,
workflow gates, auth/session gates, persistence, or production-readiness claim,
read `../shared/references/case-matrix-coverage-guard.md` and pass its
case-to-test mapping concerns into the active guard brief.

Subagent findings are evidence, not truth. Read and apply
`../shared/references/subagent-boundaries.md` when dispatching reviewers; the
main synthesis owns final classification, contradictions, and document edits.

**If no document is specified (interactive mode):** Ask which document to review, or find the most recent active-root document in `docs/brainstorms/` or `docs/plans/` using a file-search/glob tool (e.g., Glob in Claude Code). Ignore `_archive` subtrees for this inferred latest/open discovery. If the user explicitly names a document under `docs/brainstorms/_archive/` or `docs/plans/_archive/`, read that archived path directly as historical context.

**If no document is specified (headless mode):** Output "Review failed: headless mode requires a document path. Re-invoke with: Skill(\"ce-doc-review\", \"mode:headless <path>\")" without dispatching agents.

### Classify Document Type

Classify the document by reading its **content shape**, not its file path. Path is a tie-breaker hint, not the primary signal — a brainstorm-style doc placed under `docs/plans/` should still classify as `requirements`, and a plan-shaped doc under `docs/brainstorms/` should still classify as `plan`. The reviewers below operate differently depending on this classification, so misclassifying a plan-shaped doc as a requirements doc (or vice versa) produces noisy or under-scrutinized findings.

Use these signals to decide:

**`requirements` signals (what-to-build documents):**
- Frontmatter fields like `actors:`, `flows:`, `acceptance_examples:`, or `status:` carrying brainstorm-shaped values
- Section headings such as `Acceptance Examples`, `Actors`, `Key Flows`, `User Flows`, `Outstanding Questions`, `Resolve Before Planning`
- Numbered identifiers in the form `R1`, `R2`, `A1`, `F1`, `AE1` — requirement, actor, flow, and acceptance-example IDs
- Prose framing focused on user/business problem, behavior, scope boundaries, success criteria
- No implementation units, no per-unit file lists, no test scenarios attached to units

**`plan` signals (how-to-build documents):**
- Frontmatter fields like `type: feat|fix|refactor`, `origin: docs/brainstorms/...`
- Section headings such as `Implementation Units`, `Output Structure`, `Key Technical Decisions`, `Risks & Dependencies`, `System-Wide Impact`
- Numbered identifiers in the form `U1`, `U2` — implementation unit IDs
- Per-unit fields named `Goal`, `Files`, `Approach`, `Test scenarios`, `Verification`
- Repo-relative file paths to create/modify/test
- Prose framing focused on technical decisions, sequencing, and implementer-facing detail

**Tie-breaker rule.** When the content signals are mixed or sparse, fall back to path: `docs/brainstorms/` or `docs/brainstorms/_archive/` → `requirements`, `docs/plans/` or `docs/plans/_archive/` → `plan`. When neither path location applies, treat the dominant content shape as authoritative; if shape is genuinely ambiguous, default to `requirements` (the more conservative classification — it activates fewer plan-specific feasibility checks).

Pass the classification result to each persona via the `{document_type}` slot in the subagent template. Personas read this and adapt their analysis accordingly.

### Select Conditional Personas

Analyze the document content to determine which conditional personas to activate. Check for these signals:

**product-lens** -- activate when the document makes challengeable claims about what to build and why, or when the proposed work carries strategic weight beyond the immediate problem. The system's users may be end users, developers, operators, maintainers, or any other audience -- the criteria are domain-agnostic. Check for either leg:

*Leg 1 — Premise claims:* The document stakes a position on what to build or why that a knowledgeable stakeholder could reasonably challenge -- not merely describing a task or restating known requirements:
- Problem framing where the stated need is non-obvious or debatable, not self-evident from existing context
- Solution selection where alternatives plausibly exist (implicit or explicit)
- Prioritization decisions that explicitly rank what gets built vs deferred
- Goal statements that predict specific user outcomes, not just restate constraints or describe deliverables

*Leg 2 — Strategic weight:* The proposed work could affect system trajectory, user perception, or competitive positioning, even if the premise is sound:
- Changes that shape how the system is perceived or what it becomes known for
- Complexity or simplicity bets that affect adoption, onboarding, or cognitive load
- Work that opens or closes future directions (path dependencies, architectural commitments)
- Opportunity cost implications -- building this means not building something else

**design-lens** -- activate when the document contains:
- UI/UX references, frontend components, or visual design language
- User flows, wireframes, screen/page/view mentions
- Interaction descriptions (forms, buttons, navigation, modals)
- References to responsive behavior or accessibility

**security-lens** -- activate when the document contains:
- Auth/authorization mentions, login flows, session management
- API endpoints exposed to external clients
- Data handling, PII, payments, tokens, credentials, encryption
- Third-party integrations with trust boundary implications

**scope-guardian** -- activate when the document contains:
- Multiple priority tiers (P0/P1/P2, must-have/should-have/nice-to-have)
- Large requirement count (>8 distinct requirements or implementation units)
- Stretch goals, nice-to-haves, or "future work" sections
- Scope boundary language that seems misaligned with stated goals
- Goals that don't clearly connect to requirements

**evidence-coverage-auditor** -- activate when the document contains any case
matrix, UX matrix, acceptance examples, state machine, decision matrix,
LLM/provider classification, scraper-driven behavior, workflow gate,
auth/session gate, persistence, external side effect, or readiness claim. This
reviewer checks whether promised cases are mapped to verification scenarios with
the correct evidence class and whether smoke tests are being overstated as
readiness.

**adversarial** -- activate when the document contains a high-value challenge surface, not merely structural complexity. Routine plans with stated rationale are not by themselves an adversarial signal — premise/assumption work re-litigates settled questions when the only signal is "this plan is well-structured." Activate when ANY of the following holds:

- The document is a **requirements document** with 2+ challengeable claims (problem framing, solution selection, prioritization, predicted outcomes) -- premise scrutiny is core to the brainstorm phase
- The document touches a **high-stakes domain** -- auth, payments, billing, data migrations, privacy/compliance, external integrations, cryptography -- regardless of doc type or size
- The document **proposes a new abstraction, framework, or significant architectural pattern** -- regardless of doc type
- The document is a **plan with no `origin:` requirements doc** (greenfield bootstrap) -- premise wasn't validated upstream
- The document is a **plan that explicitly extends scope** beyond its origin requirements doc (new actors, new flows, deferred-then-restored features)
- The document contains an **explicit alternatives section** or unresolved tradeoffs -- adversarial helps stress-test the chosen direction

Do NOT activate adversarial on a routine plan document that derives from a validated origin requirements doc, stays within scope, and does not introduce high-stakes domains or new abstractions. The plan's structural decisions (more units, more rationale) are not by themselves adversarial signal -- those are the plan doing its job.

## Phase 2: Announce and Dispatch Personas

### Announce the Review Team

Tell the user which personas will review and why. For conditional personas, include the justification:

```
Reviewing with:
- coherence-reviewer (always-on)
- feasibility-reviewer (always-on)
- scope-guardian-reviewer -- plan has 12 requirements across 3 priority levels
- security-lens-reviewer -- plan adds API endpoints with auth flow
```

### Build Agent List

Always include:
- `coherence-reviewer`
- `feasibility-reviewer`

Add activated conditional personas:
- `product-lens-reviewer`
- `design-lens-reviewer`
- `security-lens-reviewer`
- `scope-guardian-reviewer`
- `evidence-coverage-auditor`
- `adversarial-document-reviewer`

### Dispatch

Dispatch generic subagents using **bounded parallelism** with the platform's subagent primitive (e.g., `Agent` in Claude Code, `spawn_agent` in Codex) where available; otherwise run the work inline or serially. Omit the `mode` parameter so the user's configured permission settings apply. Respect the current harness's active-subagent limit: queue selected reviewers, dispatch only as many as the harness accepts, and fill freed slots as reviewers complete. Treat active-agent/thread/concurrency-limit spawn errors as backpressure, not reviewer failure: leave the reviewer queued and retry after a slot frees. Record a reviewer as failed only after a successful dispatch times out/fails, or when dispatch fails for a non-capacity reason.

For each selected reviewer, read the matching skill-local prompt asset at `references/personas/<reviewer-name>.md` and pass its full content as `{persona_file}`. Do not dispatch standalone agents by type/name and do not rely on platform-level custom-agent registration.

**Model tiering lives here, not in prompt assets.** Local prompt files have no frontmatter and carry no model metadata. Apply these dispatch-time preferences when the platform exposes a known model override; otherwise omit the override and inherit the parent model rather than guessing a platform-specific model name:

- `coherence-reviewer`: cheapest capable extraction/reasoning tier.
- `design-lens-reviewer`, `security-lens-reviewer`, `scope-guardian-reviewer`, `evidence-coverage-auditor`: platform mid-tier model.
- `feasibility-reviewer`, `product-lens-reviewer`, `adversarial-document-reviewer`: inherit the parent model unless the harness has an established high-capability review tier.

Each subagent receives the prompt built from the subagent template included below with these variables filled:

| Variable | Value |
|----------|-------|
| `{persona_file}` | Full content of the selected local prompt asset from `references/personas/` |
| `{schema}` | Content of the findings schema included below |
| `{document_type}` | "requirements" or "plan" from Phase 1 classification |
| `{document_path}` | Path to the document |
| `{origin_path}` | Value of the document's `origin:` frontmatter field if present, or the literal string `none` if absent. Personas that adapt on origin (product-lens, adversarial, scope-guardian) read this slot to gate technique suppression — they do NOT re-parse frontmatter themselves. Extract this once during Phase 1 reading. |
| `{document_content}` | Full text of the document |
| `{decision_primer}` | Cumulative prior-round decisions in the current session, or an empty `<prior-decisions>` block on round 1. See "Decision primer" below. |
| `{active_guard_brief}` | `Active guard brief: none` unless runtime prompt-contract or Supabase/DB guard concerns triggered in Phase 1; when triggered, a concise guard block the reviewer must apply. |

Pass each subagent the **full document** — do not split into sections.

### Decision primer

On round 1 (no prior decisions), set `{decision_primer}` to:

```
<prior-decisions>
Round 1 — no prior decisions.
</prior-decisions>
```

On round 2+ (after one or more prior rounds in the current interactive session), accumulate prior-round decisions and render them as:

```
<prior-decisions>
Round 1 — applied (N entries):
- {section}: "{title}" ({reviewer}, {confidence})
  Evidence: "{evidence_snippet}"

Round 1 — rejected (M entries):
- {section}: "{title}" — Skipped because {reason}
  Evidence: "{evidence_snippet}"
- {section}: "{title}" — Deferred to Open Questions because {reason or "no reason provided"}
  Evidence: "{evidence_snippet}"
- {section}: "{title}" — Acknowledged without applying because {reason or "no suggested_fix — user acknowledged"}
  Evidence: "{evidence_snippet}"

Round 2 — applied (N entries):
...
</prior-decisions>
```

Each entry carries an `Evidence:` line because synthesis R29 (rejected-finding suppression) and R30 (fix-landed verification) both use an evidence-substring overlap check as part of their matching predicate — without the evidence snippet in the primer, the orchestrator cannot compute the `>50%` overlap test and has to fall back to fingerprint-only matching, which either re-surfaces rejected findings or suppresses too aggressively. The `{evidence_snippet}` is the first evidence quote from the finding, truncated to the first ~120 characters (preserving whole words at the boundary) and with internal quotes escaped. If a finding has multiple evidence entries, use the first one; the rest live in the run artifact and are not needed for the overlap check.

Accumulate across all rounds in the current session. Skip, Defer, and Acknowledge actions all count as "rejected" for suppression purposes — each signals the user decided the finding wasn't worth actioning this round (Acknowledge is the no-fix-guard variant: the user saw a finding with no `suggested_fix`, chose not to defer or skip explicitly, and recorded acknowledgement instead; for round-to-round suppression that is semantically equivalent to Skip). Applied findings stay on the applied list so round-N+1 personas can verify fixes landed (see R30 in `references/synthesis-and-presentation.md`).

Cross-session persistence is out of scope. A new invocation of ce-doc-review on the same document starts with a fresh round 1 and no carried primer, even if prior sessions deferred findings into the document's Open Questions section.

**Error handling:** If a subagent fails or times out, proceed with findings from subagents that completed. Note the failed reviewer in the Coverage section. Do not block the entire review on a single reviewer failure.

**Dispatch limit:** Even at maximum (7 agents), use bounded parallel dispatch. If the harness cap is lower than the selected team size, queue the remainder and launch them as active reviewers complete.

## Phases 3-5: Synthesis, Presentation, and Next Action

After all dispatched agents return, read
`../shared/references/elons-principles-order-of-operations-guard.md` and then
`references/synthesis-and-presentation.md` for the synthesis pipeline
(validate, General Finding Relevance & Subtraction Gate, anchor-based gate,
dedup, cross-persona agreement promotion, resolve contradictions,
auto-promotion, route by three tiers with FYI subsection), `safe_auto` fix
application, headless-envelope output, and the handoff to the routing question.
Apply the subtraction gate to every persona's findings before presenting or
auto-applying them: a finding is not actionable merely because it is true; it
must improve the current document's target outcome more than its smallest
adequate fix increases carrying cost.

For the four-option routing question and per-finding walk-through (interactive mode), read `references/walkthrough.md`. For the proposal-package preview used by best-judgment routing, Open-Questions-only routing, and walk-through "proposal package for the rest", read `references/bulk-preview.md`. Do not load these files before agent dispatch completes.

---

## Included References

### Subagent Template

@./references/subagent-template.md

### Findings Schema

@./references/findings-schema.json

Selected reviewer prompt assets live under `references/personas/`. Read only the prompt files selected for the current review.
