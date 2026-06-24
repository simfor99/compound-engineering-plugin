---
name: ce-skill-backup
description: "Use to back up Simon's active Compound Engineering personal plugin cache into the controlled compound-engineering-plugin fork with preview, sync, commit, or push protection."
metadata:
  short-description: Back up CE skill patches to Simon's fork
---

# CE Skill Backup

Back up Simon's active Compound Engineering personal plugin cache into the
controlled `compound-engineering-plugin` fork at
`/home/simon/plugins/compound-engineering`.

This skill is for CE skill and agent-behavior patches, not for ordinary Sanctum
application code. It keeps the installed personal plugin cache and Simon's fork
aligned without broad staging shortcuts.

This skill is self-referential: `ce-skill-backup` is part of the CE backup
surface and must travel with the CE plugin skills it protects.

## When to use

Use this skill when Simon says any of:

- "CE Skills sichern"
- "Compound Engineering Backup"
- "push die CE Skills"
- "backup das CE Plugin"
- "$ce-skill-backup"

Also use it after changing any of:

- `/home/simon/.codex/plugins/cache/personal/compound-engineering/3.13.1/skills/**`
- `/home/simon/.codex/plugins/cache/personal/compound-engineering/3.13.1/AGENTS.md`
- `/home/simon/plugins/compound-engineering/skills/**`
- `/home/simon/plugins/compound-engineering/AGENTS.md`
- `/home/simon/plugins/compound-engineering/package.json`
- CE-specific plugin manifests used by Codex, Claude, AGY or agent marketplaces
- Native OpenCode and Pi package entrypoints:
  - `.opencode/**`
  - `.pi/**`
- The CE bundle manifest and validator:
  - `skills/shared/ce-bundle.json`
  - `src/release/bundleManifest.ts`
  - the fork's root release-validation hook

## Process

1. **Preview first**

   ```bash
   python3 /home/simon/plugins/compound-engineering/skills/ce-skill-backup/scripts/backup_ce_skill_bundle.py preview
   ```

   Report `remote_status`, `cache_vs_fork`, `action_needed`, concrete
   changed/missing/stale files, and the suggested commit message. Also report
   whether `skills/shared/ce-bundle.json` exists in both the active cache and
   fork, and whether its cache-vs-fork SHA-256 checksum matches.

   If `action_needed=none`, explain that the active cache, local fork and
   remote branch are already aligned enough for backup purposes. Stop there.

   If `action_needed=apply_backup` or `commit_push`, ask exactly one decision
   question:

   ```text
   Soll ich diesen CE-Backup-Stand jetzt anwenden, validieren, committen und nach GitHub pushen?
   ```

   A user answer like "ja", "okay", "mach das" or "go" to that question is
   explicit approval for apply if needed, exact-path staging, commit and push.
   Do not ask a second time before commit or push.

2. **After approval, sync only when needed**

   ```bash
   python3 /home/simon/plugins/compound-engineering/skills/ce-skill-backup/scripts/backup_ce_skill_bundle.py apply
   ```

   This copies the active personal plugin cache's CE runtime files into the
   fork. Scope is intentionally narrow: `skills/`, `AGENTS.md`, `package.json`,
   native OpenCode/Pi entrypoints, relevant plugin/marketplace manifests, and
   release validator files. It does not rewrite unrelated upstream docs,
   release configuration, package locks, or app source.

3. **Validate after apply or before commit**

   ```bash
   python3 /home/simon/plugins/compound-engineering/skills/ce-skill-backup/scripts/backup_ce_skill_bundle.py status
   ```

   Confirm `validation=ok`. Then run repository validation from the fork when
   available:

   ```bash
   bun run release:validate
   claude plugin validate .
   git diff --check
   ```

   `bun run release:validate` is required when the fork has a Bun toolchain,
   because it runs the CE bundle manifest validator
   (`src/release/bundleManifest.ts`) against `skills/shared/ce-bundle.json`.
   If Bun is unavailable, state that clearly and do not claim bundle-manifest
   validation passed.

   After validation, prove cache/fork parity by reading back the manifest from
   both locations and comparing checksums:

   ```bash
   sha256sum \
     /home/simon/.codex/plugins/cache/personal/compound-engineering/3.13.1/skills/shared/ce-bundle.json \
     /home/simon/plugins/compound-engineering/skills/shared/ce-bundle.json
   ```

   The two hashes must match before the backup can be called aligned.

   Also run a secret scan if available:

   ```bash
   gitleaks protect --no-banner
   ```

   If `gitleaks` is unavailable, say so and use `rg` fallback for obvious
   secrets. Treat false positives explicitly; never ignore real secrets.

4. **Commit and push under the single approval**

   Follow the `smart-commit` safety contract. Do not use broad staging
   shortcuts like `git add .` or `git add -A`.

   Stage exact changed files under the backup scope only, then commit with the
   suggested message from preview, normally:

   ```text
   chore(skills): backup Compound Engineering personal plugin patches
   ```

   Push to the `fork` remote on the current branch if the single approval
   question included "pushen" and Simon answered yes/okay/mach das.

## Resources

- Script: `scripts/backup_ce_skill_bundle.py`
- Bundle manifest: `skills/shared/ce-bundle.json`
- Bundle validator: `src/release/bundleManifest.ts`
- Release validator hook: the fork's root release-validation hook
- Active cache: `/home/simon/.codex/plugins/cache/personal/compound-engineering/3.13.1`
- Destination fork: `/home/simon/plugins/compound-engineering`

## Rules

- Canonical backup target is the controlled fork checkout:
  `/home/simon/plugins/compound-engineering`.
- The active personal plugin cache is the source for backup comparison and
  apply, because that is what Codex actually loads at runtime.
- `ce-skill-backup` is self-referential and must exist under
  `skills/ce-skill-backup/` in the CE plugin source and active cache.
- The global duplicate under `/home/simon/.codex/skills/ce-skill-backup` is
  intentionally absent. If it reappears, remove it so the skill registry exposes
  only the plugin-provided `compound-engineering:ce-skill-backup` entry.
- Back up only CE runtime/agent behavior surfaces: `skills/`, `AGENTS.md`,
  `package.json`, native OpenCode/Pi entrypoints, plugin/marketplace manifests,
  and release validator files. The bundle manifest under
  `skills/shared/ce-bundle.json` is part of this runtime surface.
- Exclude `.git`, `node_modules`, caches, `__pycache__`, `.pytest_cache`,
  `.DS_Store`, and `.pyc`.
- Preview must distinguish cache-vs-fork drift from local fork changes that
  only need commit/push.
- Preview/status must distinguish ordinary file drift from bundle-manifest
  drift. Missing or mismatched `skills/shared/ce-bundle.json` is blocking for a
  "backup aligned" claim.
- The post-apply validation receipt must include:
  `bun run release:validate`, manifest checksum readback from active cache and
  fork, and `git diff --check`.
- Ask only one approval question for apply+commit+push when backup is needed.
- Never broad-stage the fork. Stage only paths reported by `git status` inside
  the backup scope.
