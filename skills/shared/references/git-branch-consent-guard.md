# Git branch consent guard

This reference is the single source of truth for Compound Engineering branch,
worktree, and branch-rename consent. Apply it before any skill creates or
renames a branch, creates a worktree, or runs a checkout command that would
materialize a new local branch.

## Default posture

Recommend, do not execute.

The default action is to leave the current git state unchanged. If the user
does not answer, gives an ambiguous answer, ignores the recommendation, or
continues with unrelated instructions, do not create or rename a branch and do
not create a worktree.

## Operations covered

This guard applies before running any of these operations or their moral
equivalents:

- `git checkout -b <branch>`
- `git switch -c <branch>`
- `git branch -m <new-name>`
- `git worktree add -b <branch> <path> <base>`
- native harness worktree creation such as `WorktreeCreate`
- branch-producing PR checkout, including `gh pr checkout`, when it would
  create a new local branch
- scripts or subagents that create experiment, review, or implementation
  branches

Read-only git inspection, `git fetch`, `git status`, `git diff`, `git branch
--show-current`, `git worktree list`, and checking whether a branch or worktree
already exists are allowed without this guard.

## Required UX

Before a covered operation, show a concise branch recommendation instead of
acting immediately.

The prompt must include:

- current branch or detached HEAD state
- recommended action: create branch, rename branch, create worktree, or no
  branch needed
- proposed branch name
- base ref, when known
- target worktree path, when relevant
- why the recommendation is useful
- what happens if the user says no or does not answer: no git state change

Use the platform's blocking question tool when available. If no blocking
question tool exists or the call fails, ask in chat and wait. Do not treat a
recommendation, a plan, a skill invocation, or a previous general preference as
approval.

## Approval standard

Proceed only after an explicit approval in the current conversation.

Acceptable approval examples:

- "ja, erstelle den Branch `<branch>`"
- "ja, Worktree mit `<branch>`"
- "Option 1" when the latest visible prompt mapped option 1 to the exact
  covered operation
- a user instruction in the same message that names the operation and branch,
  such as "create branch `feat/url-check` and continue"

Not enough:

- silence or timeout
- "weiter"
- "mach deine Empfehlung"
- "passt"
- a skill name such as `ce-worktree`
- a general preference from an older conversation
- approval for a different git operation such as commit or push

If approval is missing, continue only with read-only analysis or work that does
not require the covered operation. If the work cannot proceed safely without
the branch/worktree, stop and ask again.

## Suggested prompt

```text
Branch-Empfehlung:
- Aktuell: <current-branch-or-detached>
- Empfehlung: <create branch | rename branch | create worktree | no branch>
- Zielbranch: <branch-name>
- Basis: <base-ref>
- Worktree-Pfad: <path-or-n/a>
- Grund: <one sentence>

Ohne deine explizite Freigabe ändere ich nichts an Branches oder Worktrees.

Optionen:
1. Ja, genau so erstellen
2. Nein, im aktuellen Checkout weiterarbeiten
3. Abbrechen
```

A bare number is valid only if the latest visible prompt displayed that exact
numbered option. If the user chooses option 2, do not create or rename a
branch, and do not create a worktree.

## Interaction with commits and PRs

Commit, push, and PR approval does not imply branch approval. If a skill needs
a branch before committing or opening a PR, it must run this guard first.

On a default branch, never auto-create a feature branch. Recommend one and wait
for explicit approval. If approval is not given, do not commit to the default
branch unless the user separately and explicitly approves committing there.

## Interaction with subagents and scripts

Do not delegate branch creation to a subagent or script unless the orchestrator
has already obtained explicit approval for the exact branch/worktree shape.

The delegated instruction must include:

- approved branch name
- approved base ref
- approved worktree path, when relevant
- instruction to stop rather than choose another branch shape automatically

