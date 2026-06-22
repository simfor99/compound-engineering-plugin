# Execution Engines

`ce-work` can implement an implementation-ready unified plan with one of three engines. The engine is chosen once, after Phase 0 classifies the plan as `artifact_readiness: implementation-ready` plus `execution: code`. The engine decides *how* implementation runs; it never changes *who* owns the shipping tail (see "Tail ownership" below).

Engine selection applies only to code execution. Knowledge-work and legacy plans keep the inline/subagent flow in `SKILL.md`.

## Step 1: Probe host capability

An engine is usable only when the host actually exposes a callable primitive for it. Do not assume one exists from its name.

| Engine | Usable when | Claude Code reality |
|---|---|---|
| **Inline / subagent** | Always. The orchestrator runs units inline or dispatches subagents via the platform's subagent primitive (`Agent`/`Task` in Claude Code, `spawn_agent` in Codex, `subagent` in Pi). | Always callable in-session. This is the default. |
| **Goal-mode** | The host exposes a callable persistent-objective primitive that runs to completion, returns control, and yields a structured completion summary. | **Not callable from inside a skill.** `/goal` is a top-level user command. `ce-work` cannot invoke it mid-session — it can only emit a copyable prompt for the user to paste, or run inline/subagents. |
| **Dynamic-workflow** | The host exposes a callable dynamic-workflow / ultracode-style orchestration primitive that returns structured results and blockers without mid-run user decisions. | **Not callable from inside a skill.** Dynamic workflows start from a user prompt (`ultracode:` or `/effort ultracode`). `ce-work` can only emit a copyable prompt block. |

Rule of thumb: if the host primitive cannot be *called and awaited from within this skill*, treat goal-mode and dynamic-workflow as **prompt-emission only**, not as internal engines. On Claude Code, both fall in the copy/paste bucket; the only internally callable engine is inline/subagent.

**Codex specifically.** Codex `/goal` is a top-level thread mode with pause/resume/clear/view controls — not an awaitable subroutine a skill can call and collect a structured completion envelope from. Treat it like Claude Code: prompt-emission only for standalone use, inline/subagents for LFG/caller-owned-tail. Run goal-mode internally only if a future Codex runtime exposes a callable goal primitive the skill can start and observe to completion/blocked. This constraint binds the native Codex plugin install too, which loads `SKILL.md` verbatim.

## Step 2: Pick the engine by plan shape

When more than one engine is callable, choose by the plan's decomposition shape:

| Plan shape | Engine | Why |
|---|---|---|
| Sequential or modest U-ID decomposition; units share files or depend on each other | **Inline / subagent** (default), or a **goal-mode** prompt for sustained focus when callable | The DoD already defines the end condition; ordinary persistence finishes it. |
| Many independent U-IDs with disjoint file ownership; codebase-wide sweep; large migration; adversarial cross-checking | **Dynamic-workflow** when callable; otherwise parallel subagents | Workflow scripts hold branching, loops, and intermediate worker state outside the main context and coordinate many agents. Prefer this over goal-mode for large fan-out. |
| Host exposes no callable goal/workflow primitive (e.g. Claude Code in-session) | **Inline / subagent** | Preserve the same Reader Index / DoD / U-ID discipline without relying on unavailable host features. |

Recommend exactly one path. Present a non-default engine as an "advanced / large-scale option" only when the plan shape plausibly warrants it — never as an equal coin-flip.

## Step 3: Run the chosen engine

### Inline / subagent (default)

Follow the dispatch strategy in `SKILL.md` Phase 1 Step 4 (inline, serial subagents, or parallel subagents) and the Phase 2 execution loop. `ce-work` owns task creation, unit sequencing, dispatch, verification, and commits.

### Goal-mode and dynamic-workflow

On a host where these are not callable from a skill (Claude Code today): do **not** attempt to invoke them. Instead:

- **Standalone interactive use:** print a copyable prompt block for the user to paste, then continue inline/subagents if the user does not paste it. Do not stall waiting for a paste.
- **Caller-owned-tail use (e.g. under `lfg`):** do **not** emit a copyable prompt — a manual paste step strands the caller. Run inline/subagents instead, or return a blocker if the plan genuinely requires an unavailable engine.

On a host where they *are* callable: launch the engine scoped to implementation only, await its structured summary, then resume the tail (below). The launched goal/workflow must not open a PR, finalize the session, or bypass the owning workflow's gates.

Copyable goal-mode prompt (standalone — emit verbatim, with the literal plan path substituted):

```text
/goal Implement <plan-path> through its Definition of Done.

First read: Reader Index, Goal Capsule, Definition of Done, and the Implementation Units heading map. Work unit-by-unit. For each U-ID, read only that unit plus referenced R/F/AE/KTD sections. Track progress outside the doc. Before each major phase and before declaring done, re-open the plan path and re-check the active U-IDs, Verification Contract, and Definition of Done against the current diff — context may have been compacted to a summary that dropped detail.

This top-level goal owns implementation quality gates: run simplification and code review when the diff meets the repo's normal criteria, apply eligible fixes, and surface residual findings. Do not open a PR.

Done when the transcript shows: all non-deferrable U-IDs completed; each Per-Unit DoD row has an observed verification result; required repo checks passed or are documented as not applicable; applicable simplification/review gates ran or were explicitly skipped with reason; dead-end or experimental code from approaches that did not pan out has been removed from the diff; no plan body progress/status was written; and no PR was opened. Stop early only when a named blocker prevents completion.
```

Copyable dynamic-workflow prompt (large fan-out — emit verbatim):

```text
ultracode: Execute <plan-path> as an end-to-end dynamic workflow.

Use the plan as authority. Build the workflow around the Implementation Units and Definition of Done. Parallelize only independent U-IDs with disjoint file ownership, keep intermediate agent results inside the workflow, run simplification/review/verification gates inside the workflow tail, and return a final summary with changed files, U-IDs completed, verification results, residual findings, and blockers.
```

Keep emitted prompts under 4,000 characters and always substitute the literal plan path.

## Step 4: Resume the correct tail

After any engine finishes implementation, inspect the diff and continue at the tail that matches the caller. The engine never owns more than implementation + local verification on its own.

| Mode | After implementation, `ce-work` ... |
|---|---|
| **Standalone** (user invoked `ce-work` directly, or `ce-plan` handed off interactively) | Resumes its normal post-implementation tail — Phase 3-4 quality gates, simplification, review, commit, and handoff in `references/shipping-workflow.md`. A goal-mode run does not skip these; verify they ran or were explicitly skipped with reason. |
| **Caller-owned-tail** (`mode:caller-owned-tail`, e.g. under `lfg`) | Performs implementation and local verification only, then returns the structured summary in `SKILL.md` § Caller-Owned Tail Mode (`standalone_shipping_skipped: true`). Does not run simplify/review/PR/CI — the caller owns those. |

Using goal-mode or a dynamic workflow is a way to get better sustained implementation focus, not a way to skip the owning workflow's finish discipline.

## Progress visibility (independent of tail ownership)

Tail ownership decides who opens the **final** PR; it does not forbid progress signals during a long run. For multi-hour goals, meaningful commits as units complete and an optional scratch progress artifact (outside the plan body) are encouraged so a long trajectory stays observable. Only final PR creation is gated: a standalone top-level goal may open a **draft** PR only when it explicitly owns that channel; in caller-owned-tail mode `ce-work` must not open any PR, but may commit and return a progress report in its structured envelope. Never write progress or status into the plan body — git, commits, and the envelope carry it.
