---
name: ce-worktree
description: Ensure work happens in an isolated git worktree without disturbing the current checkout. Use when starting work that should stay isolated, or when `ce-work` or `ce-code-review` offers a worktree option. Detects existing isolation first, prefers the harness's native worktree tool, and falls back to plain git.
---

# Worktree Isolation

Ensure the current work happens in an isolated workspace, without disturbing the user's main checkout. Most coding harnesses now create a worktree by default at session start, so the common case is that **isolation already exists** — detect that first and do not create a redundant one.

Order of operations: **detect existing isolation -> prefer a native worktree tool -> fall back to plain git.** Never create a worktree the harness cannot see.

Before creating any worktree or branch, load and follow
`../shared/references/git-branch-consent-guard.md`. This skill may recommend
worktree isolation, but invoking the skill is not consent to create a worktree.
If the user does not explicitly approve the exact branch/worktree shape, leave
git state unchanged.

## Step 0: Detect existing isolation

Before creating anything, check whether the current directory is already a linked worktree. Compare the **resolved absolute** git dir against the **resolved absolute** common git dir — resolve each to an absolute path first and compare those, not the raw `git rev-parse` output. Git mixes absolute and relative forms depending on the current directory (from a subdirectory of a normal checkout, `--git-dir` comes back absolute while `--git-common-dir` may be relative), so a raw string compare yields a false "already isolated":

```bash
git rev-parse --absolute-git-dir                     # absolute git dir for this worktree
(cd "$(git rev-parse --git-common-dir)" && pwd -P)   # absolute shared (common) git dir
```

If the two absolute paths are **equal**, this is a normal checkout — continue to Step 1.

If they **differ**, you are in a linked worktree *or* a submodule. Distinguish them:

```bash
git rev-parse --show-superproject-working-tree
```

- **Non-empty** output -> you are in a submodule; treat it as a normal checkout and continue to Step 1.
- **Empty** output -> you are **already in an isolated worktree**. Report the worktree path (`git rev-parse --show-toplevel`) and current branch, and **work in place**. Do not create another worktree — a worktree-from-worktree lands in the wrong tree and is invisible to the harness that made the current one.

#### Worktree Runtime Environment And Server Guard

When the worktree will run a local server, browser test, workflow, auth path,
Supabase-backed endpoint, provider call, scraper, queue, trace writer, or any
other live-ish runtime, treat the worktree as a new machine until proven
otherwise. Worktree isolation only copies Git-tracked files; ignored local
runtime files such as `.env.local` are usually absent. Do this handoff before
starting a server, opening a browser, or claiming live evidence:

1. Classify the intended evidence before setup:
   - `ui_static` / `mock_render`: no live backend claim.
   - `ui_auth` / `api_live` / `workflow_live` / `provider_live`: real runtime
     claim; env and backend preflight are mandatory.
2. Compare repo-root env files in the current worktree against the original
   checkout or base repo when it is known (`.env`, `.env.local`,
   `.env.development`, `.env.test`). Report only presence/absence and required
   key names; never print secret values.
3. Identify required key names from `.env.example`, route docs, the target
   command, and the target runtime path. Keep client and server env separate:
   Vite `VITE_*` values can unblock browser rendering, but they do not provide
   server-only credentials such as `SUPABASE_SERVICE_ROLE_KEY`.
4. If required local-only env files are absent from the worktree, stop before
   starting runtime and choose one explicit env source:
   - source the main checkout's local env at server start,
   - create a local non-committed env file/symlink if the repo convention
     already allows it and state the source path,
   - use dummy values only for explicit mock/render evidence,
   - or mark the live/runtime gate as blocked.
5. Dummy or placeholder credentials may be used only for mock/render/smoke
   evidence. They cannot support a claim about live auth, Supabase persistence,
   workflow start, provider calls, scraper output, or production readiness.
6. If a route requires both a build-time/client flag and a server/runtime flag,
   verify both before opening the browser. Example shape:
   `VITE_E2E_CONTEXT_ENTRY=1` is not the same proof as
   `GTM_AUDIT_E2E_CONTEXT_ENTRY=1`.
7. Before any registry-managed dev server start, run registry `status` or
   `scan` read-only. Reuse an existing server only when its project path,
   worktree/branch, port, command, and env source match the intended evidence.
   If the registry cannot prove env equivalence, treat the server as
   unverified until a backend preflight passes.
8. In WSL/Windows setups where the server registry opens a visible terminal,
   do not loop through visible server restarts with different env guesses. One
   wrong visible start is enough evidence to stop, clean up or report the
   blocker, and ask before trying another visible start.
9. Before handing a visible URL to the user, run a minimal preflight that hits
   the same class of backend path expected by the manual test. If the real
   endpoint is not exercised, label the browser session as UI-only or mocked.
10. The handoff must include the env source class (`repo_env_file`,
   `main_checkout_env_source`, `local_symlink`, `explicit_export`,
   `dummy_mock_env`, or `blocked_missing_env`), the server path/port, and the
   evidence class claimed.

## Step 1: Prefer the harness's native worktree tool

If the harness provides a native worktree primitive — for example an `EnterWorktree` / `WorktreeCreate` tool, a `/worktree` command, or a `--worktree` flag — use it only after the branch consent guard approves the exact branch/worktree shape, then stop. Native tools place, track, and clean up the worktree so the harness can manage it. A behind-the-back `git worktree add` creates phantom state the harness cannot see, navigate to, or clean up.

External worktree pool managers such as Treehouse are not the default for this
CE skill. Use them only when the user explicitly asks for that tool, when a
separate Treehouse-specific skill owns the flow, or when the harness itself
exposes Treehouse as its native worktree primitive. Do not add Treehouse to fix
an env/server problem; fix the env/server handoff above.

## Step 2: Git fallback

Only when there is no native tool **and** Step 0 found no existing isolation.

1. **Run from the repo root.** The `.worktrees/` and `.gitignore` paths below are repo-root-relative, but the skill runs from the user's current directory, which may be a subdirectory — so move to the root first: `cd "$(git rev-parse --show-toplevel)"`. Without this, `.worktrees/<branch>` and the `.gitignore` edit would land in the subdirectory (e.g. `src/.worktrees/...`, `src/.gitignore`) instead of at the repo root.
2. Choose a meaningful branch name from the work description (e.g. `feat/login`, `fix/email-validation`) — avoid opaque auto-generated names. Pick a base branch (default: origin's default branch, else `main`). Present the branch name, base branch, and worktree path through the branch consent guard before creating anything.
3. **Ensure `.worktrees/` is gitignored before creating anything**, so worktree contents are never committed: check `git check-ignore -q .worktrees/` — **with the trailing slash**, so an existing directory-only `.worktrees/` rule is honored even before the directory exists (`git check-ignore .worktrees` without the slash would miss it and dirty a correctly-configured repo). If it is not ignored, add a `.worktrees/` line to `.gitignore`.
4. Best-effort refresh the base branch without disturbing the current checkout: `git fetch origin <from-branch>`. This is **non-fatal** — if it errors (no `origin` remote, a differently-named remote, or a local-only branch), do not abort; continue to the next step and use the local ref.
5. Create the worktree from the remote base when available, else the local ref: `git worktree add -b <branch-name> .worktrees/<branch-name> origin/<from-branch>`. If `origin/<from-branch>` does not exist, use the local `<from-branch>` ref instead.
6. Switch into it: `cd .worktrees/<branch-name>`.

If `git worktree add` fails with a sandbox or permission error, the requested isolation could not be created. This needs a **blocking** user decision before touching the current checkout — do not silently continue there (the user chose isolation specifically to avoid it, especially when `ce-work` / `ce-code-review` routed here for the worktree option). Report the failure and ask via the platform's blocking question tool: `AskUserQuestion` in Claude Code (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded), `request_user_input` in Codex, `ask_question` in Antigravity CLI (`agy`), `ask_user` in Pi (via the `pi-ask-user` extension) — offering options such as "work in the current checkout" vs "stop and resolve the permission issue". If no blocking tool exists in the harness or the call errors, present the numbered options in chat and wait for the reply; never skip the confirmation. Only work in the current checkout on explicit confirmation, and do not retry alternative paths automatically.

## Other worktree operations

Use `git` directly — no wrapper is needed:

```bash
git worktree list                          # list worktrees
git worktree remove .worktrees/<branch>    # remove a worktree
cd .worktrees/<branch>                     # switch to a worktree
cd "$(git rev-parse --show-toplevel)"      # return to the current checkout root
```

## When to create a worktree

Create one (Step 1/2) only when you are **not** already isolated, you need a separate workspace, and the user explicitly approved the exact branch/worktree shape:

- Reviewing a PR while keeping the current checkout free for other work
- Running multiple features in parallel without branch-switching overhead

Do not create a worktree for single-task work that can happen on a branch in the current checkout — and never when Step 0 shows you are already in one.

## Integration

`ce-work` and `ce-code-review` offer this skill as an option. When the user selects "worktree" in those flows, run Step 0 first: if the work is already isolated, proceed in place; otherwise recommend one (native tool preferred) with a meaningful branch name derived from the work description, then follow the branch consent guard before creating it.

## Troubleshooting

**"Worktree already exists"**: the path is in use. Switch to it (`cd .worktrees/<branch>`) or remove it (`git worktree remove .worktrees/<branch>`) before recreating.

**"Cannot remove worktree: it is the current worktree"**: `cd` out of the worktree first, then `git worktree remove`.
