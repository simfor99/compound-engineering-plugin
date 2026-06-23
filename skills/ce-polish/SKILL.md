---
name: ce-polish
description: "Start the dev server, open the feature in a browser, and iterate on improvements together. Manual invocation only — type /ce-polish to run it."
disable-model-invocation: false
argument-hint: "[PR number, branch name, or blank for current branch]"
---

# Polish

Start the dev server, open the feature in a browser, and iterate. You use the feature, say what feels off, and fixes happen.

## Browser Runtime Routing Guard

For visual UI/UX/design work, prefer Chrome-AXI against the project-approved
Chrome when it is available. This is the fastest default path for seeing the
real rendered page, taking screenshots, and checking console/network evidence.

Fallbacks:
- Use direct Chrome DevTools MCP when AXI is unavailable or a specialized CDP
  operation needs it.
- Use `agent-browser` for quick exploration when no live/auth/session or
  extension-runtime proof is being claimed.
- Use Playwright only after Chrome-AXI observation when an important behavior
  should be codified as an automated regression, or when the user explicitly
  asks for CI/headless, Cross-Browser, scripted multi-viewport, or complex-loop
  evidence.

Browser automation uses owned tabs and closes them when the polish loop ends.
Operational Chrome-AXI route: read
`/home/simon/.codex/references/chrome-devtools-axi.md`, verify
`command -v chrome-devtools-axi`, classify the project-approved Chrome endpoint,
set `CHROME_DEVTOOLS_AXI_BROWSER_URL` when needed, then use `pages`,
`newpage <url> --background`, `pages` to identify the owned tab id,
`selectpage`, `screenshot`, `console`/`network`, and `closepage` on that owned
tab. Background tabs are the default for autonomous reviews; do not bring tabs
to the front unless Simon explicitly asks or manual visual inspection cannot be
done from screenshots/snapshots. Use `newpage about:blank` only when the
specific run needs a blank starting tab.
Partial Tool Exposure: if only some AXI/Chrome-DevTools actions are visible at
first, refresh/discover capabilities and reload the AXI reference before
falling back. Do not use Playwright merely because screenshot/snapshot/navigation
was not exposed on the first look.
Patch registry: in repos that define
`docs/architecture/compound-engineering-skill-patches/002-ce-browser-runtime-routing-guard.md`,
that registry entry is the recovery source if this plugin cache is refreshed.

## Phase 0: Get on the right branch

1. If a PR number or branch name was provided, check it out (probe for existing worktrees first).
2. If blank, use the current branch.
3. Verify the current branch is not main/master.

## Phase 1: Start the dev server

### 1.1 Check for `.claude/launch.json`

Run `bash scripts/read-launch-json.sh`. If it finds a configuration, use it — the user already told us how to start the project.

### 1.2 Auto-detect (when no launch.json)

Run `bash scripts/detect-project-type.sh` to identify the framework.

Route by type to the matching recipe reference for start command and port defaults:

| Type | Recipe |
|------|--------|
| `rails` | `references/dev-server-rails.md` |
| `next` | `references/dev-server-next.md` |
| `vite` | `references/dev-server-vite.md` |
| `nuxt` | `references/dev-server-nuxt.md` |
| `astro` | `references/dev-server-astro.md` |
| `remix` | `references/dev-server-remix.md` |
| `sveltekit` | `references/dev-server-sveltekit.md` |
| `procfile` | `references/dev-server-procfile.md` |
| `unknown` | Ask the user how to start the project |

For framework types that need a package manager, run `bash scripts/resolve-package-manager.sh` and substitute the result into the start command.

Resolve the port with `bash scripts/resolve-port.sh --type <type>`.

### 1.3 Start the server

Start the dev server in the background, log output to a temp file. Probe `http://localhost:<port>` for up to 30 seconds. If it doesn't come up, show the last 20 lines of the log and ask the user what to do.

### 1.4 Open in browser

Load `references/ide-detection.md` for the env-var probe table. If Chrome-AXI
is available and the project-approved Chrome can be reached, open the feature
there in an owned tab. Otherwise open the browser using the IDE's mechanism
(Claude Code → `open`, Cursor → Cursor browser, VS Code → Simple Browser).

Tell the user:
```
Dev server running on http://localhost:<port>
Browse the feature and tell me what could be better.
```

## Phase 2: Iterate

This is the core loop. The user browses the feature and tells you what to improve. You fix it. Repeat until they're happy.

- When the user describes something to fix → make the change, the dev server hot-reloads
- When the user asks to check something → prefer Chrome-AXI to screenshot or inspect the page; use direct Chrome DevTools MCP or `agent-browser` as fallback based on the Browser Runtime Routing Guard
- When the user says they're done → commit the fixes and stop

No checklist. No envelope. Just conversation.

## References

Reference files (loaded on demand):
- `references/launch-json-schema.md` — launch.json schema + per-framework stubs
- `references/ide-detection.md` — host IDE detection and browser-handoff
- `references/dev-server-detection.md` — port resolution documentation
- `references/dev-server-rails.md` — Rails dev-server defaults
- `references/dev-server-next.md` — Next.js dev-server defaults
- `references/dev-server-vite.md` — Vite dev-server defaults
- `references/dev-server-nuxt.md` — Nuxt dev-server defaults
- `references/dev-server-astro.md` — Astro dev-server defaults
- `references/dev-server-remix.md` — Remix dev-server defaults
- `references/dev-server-sveltekit.md` — SvelteKit dev-server defaults
- `references/dev-server-procfile.md` — Procfile-based dev-server defaults

Scripts (invoked via `bash scripts/<name>`):
- `scripts/read-launch-json.sh` — launch.json reader
- `scripts/detect-project-type.sh` — project-type classifier
- `scripts/resolve-package-manager.sh` — lockfile-based package-manager resolver
- `scripts/resolve-port.sh` — port resolution cascade
