---
name: ce-test-browser
description: Run browser tests on pages affected by current PR or branch
argument-hint: "[PR number, branch name, 'current', or --port PORT]"
---

# Browser Test Skill

Run browser tests on pages affected by a PR or branch changes using the
project-appropriate browser route.

## Browser Runtime Routing Guard

Default to Chrome-AXI headless for local visual UI/UX/design inspection. Do not
connect to Simon's visible Chrome unless live auth/session/extension evidence is
the point. Use `127.0.0.1:<port>` rather than `localhost:<port>` for local WSL
dev servers. Use Chrome-AXI against the project-approved visible Chrome for
auth/session, Chrome extension, Native Messaging, CDP, performance, or
user-browser-near evidence. Direct Chrome DevTools MCP is the fallback when AXI
is unavailable or a specialized CDP operation needs it.

Use `agent-browser` for fast exploration when no live/auth/session or
extension-runtime proof is being claimed, or when Chrome-AXI is unavailable and
the test is still useful as visual/debug evidence.

Use Playwright after Chrome-AXI observation when an important behavior should be
codified as an automated regression, or when CI/headless/Cross-Browser evidence
is explicitly required.

Do not treat Xvfb, Chrome for Testing, isolated Playwright contexts, or CDP
reachability alone as proof of a real user browser, real account session, or
real extension runtime. Browser automation uses owned tabs and closes them
after the run.

Operational Chrome-AXI route: read
`/home/simon/.codex/references/chrome-devtools-axi.md`, verify
`command -v chrome-devtools-axi`, then for local UI evidence use
`env -u CHROME_DEVTOOLS_AXI_HEADED -u CHROME_DEVTOOLS_AXI_BROWSER_URL -u CHROME_DEVTOOLS_AXI_AUTO_CONNECT`
with `newpage http://127.0.0.1:<port>/<route> --background`, `pages`,
`selectpage`, `screenshot`, `console`/`network`, and `closepage` on that owned
tab. Classify and set `CHROME_DEVTOOLS_AXI_BROWSER_URL` only when a real
existing browser session, login, or extension runtime is proof-relevant. Use
`newpage about:blank` only when the specific run needs a blank starting tab.

Partial Tool Exposure: if only some AXI/Chrome-DevTools actions are visible at
first, refresh/discover capabilities and reload the AXI reference before
falling back. Do not use Playwright merely because screenshot/snapshot/navigation
was not exposed on the first look.

Patch registry: in repos that define
`docs/architecture/compound-engineering-skill-patches/002-ce-browser-runtime-routing-guard.md`,
that registry entry is the recovery source if this plugin cache is refreshed.

Use the selected route for opening pages, clicking elements, filling forms,
taking screenshots, checking console/network, and scraping rendered content.

## Evidence Authenticity Guard

Before building or reporting a browser test matrix, read and apply
`../shared/references/evidence-authenticity-guard.md` when any scenario could be
mocked, replayed, simulated, cached, fixture-backed, or confused with a live
runtime claim. Browser evidence alone proves what the browser observed. If the
claim depends on a backend call, scraper, LLM/provider call, auth boundary,
persistence, email, payment, or workflow side effect, pair the browser evidence
with network/server/provider/trace evidence or report the live leg as untested
or blocked.

## Runtime Prompt Contract Guard

When a browser scenario claims prompt fidelity, model-visible data, structured
LLM output, provider request behavior, workflow-stage prompt behavior, or live
LLM/provider readiness, read and apply
`../shared/references/ce-runtime-prompt-contract-guard.md`. Browser observation
alone does not prove rendered prompts, effective provider requests, output
contract conformance, or downstream handoff survival.

## Supabase/DB Side-Effect Guard

When a browser scenario claims Supabase, Postgres, database, migration, RLS,
auth/session persistence, storage, queue, trace indexing, durable status,
admin-log, audit-log, code-redemption, or other persistence behavior, read and
apply `../shared/references/supabase-database-change-guard.md`. Browser
observation alone does not prove schema, policy, row/object persistence,
downstream reload, or target-database readiness. Pair the browser path with
same-target write-read evidence or report the database leg as `blocked`,
`deferred`, or `not_claimed`.

Platform-specific hints:
- In Claude Code, do not use Chrome MCP tools (`mcp__claude-in-chrome__*`).
- In Codex, prefer `chrome-devtools-axi` for the Chrome-AXI route and direct
  Chrome DevTools MCP only when AXI is unavailable or insufficient.

## Prerequisites

- Local development server running (e.g., `bin/dev`, `rails server`, `npm run dev`)
- Chrome-AXI, Chrome DevTools MCP, `agent-browser`, or Playwright available for
  the selected browser route
- Git repository with changes to test

## Setup

Check whether the preferred browser route is available:

```bash
command -v chrome-devtools-axi >/dev/null 2>&1 && echo "chrome-devtools-axi installed" || echo "chrome-devtools-axi not installed"
command -v agent-browser >/dev/null 2>&1 && echo "agent-browser installed" || echo "agent-browser not installed"
```

If neither Chrome-AXI/direct Chrome DevTools nor `agent-browser` nor Playwright
is available, inform the user which route was needed and stop. Do not silently
downgrade a live/auth/session or extension-runtime claim to an isolated browser.

## Workflow

### 1. Verify Installation

Before starting, choose and verify the route using the Browser Runtime Routing
Guard:

```bash
command -v chrome-devtools-axi >/dev/null 2>&1 && echo "Chrome-AXI ready" || true
command -v agent-browser >/dev/null 2>&1 && echo "agent-browser ready" || true
```

If the selected route is unavailable, report that route and choose the next
valid fallback only if it still proves the required runtime class.

### 2. Ask Browser Mode

**Pipeline mode (`mode:pipeline`):** Skip this step entirely. If the selected
route is Chrome-AXI against a project-approved real Chrome, use an owned background tab in
that browser. Otherwise default to headless where the selected route supports
it. Proceed directly to step 3.

**Manual mode:** Ask the user whether to run headed or headless using the platform's blocking question tool: `AskUserQuestion` in Claude Code (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded), `request_user_input` in Codex, `ask_question` in Antigravity CLI (`agy`), `ask_user` in Pi (requires the `pi-ask-user` extension). Fall back to presenting options in chat only when no blocking tool exists in the harness or the call errors (e.g., Codex edit modes) — not because a schema load is required. Never silently skip the question:

```
Do you want to watch the browser tests run?

1. Headed (watch) - Opens visible browser window so you can see tests run
2. Headless (faster) - Runs in background, faster but invisible
```

Store the choice. Use the route's equivalent headed/visible mode when the user
selects option 1; for `agent-browser`, use the `--headed` flag.

### 3. Determine Test Scope

**If PR number provided:**
```bash
gh pr view [number] --json files -q '.files[].path'
```

**If 'current' or empty:**
```bash
git diff --name-only main...HEAD
```

**If branch name provided:**
```bash
git diff --name-only main...[branch]
```

### 4. Map Files to Routes

Map changed files to testable routes:

| File Pattern | Route(s) |
|-------------|----------|
| `app/views/users/*` | `/users`, `/users/:id`, `/users/new` |
| `app/controllers/settings_controller.rb` | `/settings` |
| `app/javascript/controllers/*_controller.js` | Pages using that Stimulus controller |
| `app/components/*_component.rb` | Pages rendering that component |
| `app/views/layouts/*` | All pages (test homepage at minimum) |
| `app/assets/stylesheets/*` | Visual regression on key pages |
| `app/helpers/*_helper.rb` | Pages using that helper |
| `src/app/*` (Next.js) | Corresponding routes |
| `src/components/*` | Pages using those components |

Build a list of URLs to test based on the mapping.

### 5. Detect and Claim a Free Port

**Pipeline mode only (`mode:pipeline`):** When invoked from LFG or another automated pipeline, always find a port that is actually free — never assume 3000 is available, as multiple agents may be running in parallel on the same machine.

**Manual mode (no `mode:pipeline`):** Use the preferred port as-is. Do not scan for alternatives — the user controls their own server.

Determine the preferred port using this priority:

1. **Explicit argument** — if the user passed `--port 5000`, use that directly (skip free-port scan)
2. **In-context project instructions** — if your active project instructions already in context explicitly state the dev-server port, use it. Don't grep instruction files for a port: prose mentions (docs, examples, troubleshooting) are unreliable and false-positive-prone — config files and `.env` are the trustworthy sources.
3. **package.json** — check dev/start scripts for `--port` flags
4. **Environment files** — check `.env`, `.env.local`, `.env.development` for `PORT=`
5. **Default** — fall back to `3000`

**In pipeline mode**, verify the preferred port is free and scan upward if not. **In manual mode**, use the preferred port directly.

```bash
# Step 1: Determine preferred port.
# If your in-context project instructions state the dev-server port, set PORT
# here first (e.g. EXPLICIT_PORT). Do not grep instruction files for a port.
PORT="${EXPLICIT_PORT:-}"
if [ -z "$PORT" ]; then
  PORT=$(grep -Eo '\-\-port[= ]+[0-9]{4,5}' package.json 2>/dev/null | grep -Eo '[0-9]{4,5}' | head -1)
fi
if [ -z "$PORT" ]; then
  PORT=$(grep -h '^PORT=' .env .env.local .env.development 2>/dev/null | tail -1 | cut -d= -f2)
fi
PORT="${PORT:-3000}"

# Step 2 (pipeline mode only): scan for a free port
if [ "${PIPELINE_MODE}" = "1" ]; then
  find_free_port() {
    local p=$1
    while lsof -i ":$p" -sTCP:LISTEN -t >/dev/null 2>&1; do
      p=$((p + 1))
    done
    echo $p
  }
  PORT=$(find_free_port "$PORT")
fi
echo "Using dev server port: $PORT"
```

Set `PIPELINE_MODE=1` in your shell when the argument `mode:pipeline` is present.

### 6. Start Dev Server if Not Running, Then Verify

**Pipeline mode only:** If no server is already listening on `$PORT`, start one automatically in the background. In manual mode, inform the user and stop.

```bash
if lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Server already running on port ${PORT}"
else
  if [ "${PIPELINE_MODE}" = "1" ]; then
    # Auto-start in pipeline — pick the right command for this project
    echo "Starting dev server on port ${PORT}..."
    if [ -f "bin/dev" ]; then
      PORT=${PORT} bin/dev > /tmp/dev-server-${PORT}.log 2>&1 &
    elif [ -f "bin/rails" ]; then
      bin/rails server -p ${PORT} > /tmp/dev-server-${PORT}.log 2>&1 &
    elif [ -f "package.json" ]; then
      PORT=${PORT} npm run dev > /tmp/dev-server-${PORT}.log 2>&1 &
    fi
    # Wait up to 30 seconds for server to become ready
    for i in $(seq 1 30); do
      lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1 && break
      sleep 1
    done
    if ! lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "Server did not start in 30s. Last output:"
      tail -20 /tmp/dev-server-${PORT}.log 2>/dev/null
      exit 1
    fi
  else
    # Manual mode — ask the user to start the server
    echo "Server not running on port ${PORT}"
    echo ""
    echo "Please start your development server:"
    echo "  Rails: bin/dev  or  rails server -p ${PORT}"
    echo "  Node/Next.js: npm run dev"
    echo "  Custom port: run this skill again with --port <your-port>"
    exit 0
  fi
fi

Open `http://127.0.0.1:${PORT}` with Chrome-AXI headless for local browser
tests. Use `http://localhost:${PORT}` for non-AXI tools only when that route is
known to work. Fall back according to the Browser Runtime Routing Guard.
```

### 7. Test Each Affected Page

For each affected route:

**Navigate and capture evidence:**

Use the selected browser route. With Chrome-AXI headless, open the route in an
owned tab using `http://127.0.0.1:${PORT}` and capture
screenshot/console/network evidence as needed. With `agent-browser`, the
fallback shape is:

```bash
agent-browser open "http://localhost:${PORT}/[route]"
agent-browser snapshot -i
```

**For headed mode:**
```bash
agent-browser --headed open "http://localhost:${PORT}/[route]"
agent-browser --headed snapshot -i
```

**Verify key elements:**
- Use Chrome-AXI page inspection or `agent-browser snapshot -i` to get interactive elements with refs
- Page title/heading present
- Primary content rendered
- No error messages visible
- Forms have expected fields

**Test critical interactions:**

Use the selected route. `agent-browser` fallback example:

```bash
agent-browser click @e1
agent-browser snapshot -i
```

**Take screenshots:**

Use Chrome-AXI screenshots when it is the selected route. `agent-browser`
fallback example:

```bash
agent-browser screenshot page-name.png
agent-browser screenshot --full page-name-full.png
```

### 8. Human Verification (When Required)

Pause for human input when testing touches flows that require external interaction:

| Flow Type | What to Ask |
|-----------|-------------|
| OAuth | "Please sign in with [provider] and confirm it works" |
| Email | "Check your inbox for the test email and confirm receipt" |
| Payments | "Complete a test purchase in sandbox mode" |
| SMS | "Verify you received the SMS code" |
| External APIs | "Confirm the [service] integration is working" |

Ask the user (using the platform's question tool, or present numbered options and wait):

```
Human Verification Needed

This test touches [flow type]. Please:
1. [Action to take]
2. [What to verify]

Did it work correctly?
1. Yes - continue testing
2. No - describe the issue
```

### 9. Handle Failures

When a test fails:

1. **Document the failure:**
   - Screenshot the error state with the selected browser route
   - Note the exact reproduction steps

2. **Ask the user how to proceed:**

   ```
   Test Failed: [route]

   Issue: [description]
   Console errors: [if any]

   How to proceed?
   1. Fix now - debug and fix the failing test
   2. Skip - continue testing other pages
   ```

3. **If "Fix now":** investigate, propose a fix, apply, re-run the failing test
4. **If "Skip":** log as skipped, continue

### 10. Test Summary

After all tests complete, present a summary:

```markdown
## Browser Test Results

**Test Scope:** PR #[number] / [branch name]
**Server:** http://localhost:${PORT}

### Pages Tested: [count]

| Route | Status | Notes |
|-------|--------|-------|
| `/users` | Pass | |
| `/settings` | Pass | |
| `/dashboard` | Fail | Console error: [msg] |
| `/checkout` | Skip | Requires payment credentials |

### Console Errors: [count]
- [List any errors found]

### Human Verifications: [count]
- OAuth flow: Confirmed
- Email delivery: Confirmed

### Failures: [count]
- `/dashboard` - [issue description]

### Result: [PASS / FAIL / PARTIAL]
```

## Quick Usage Examples

```bash
# Test current branch changes (auto-detects port)
/ce-test-browser

# Test specific PR
/ce-test-browser 847

# Test specific branch
/ce-test-browser feature/new-dashboard

# Test on a specific port
/ce-test-browser --port 5000
```

## agent-browser Fallback CLI Reference

Run `agent-browser --help` for all commands.

Key commands:

```bash
# Navigation
agent-browser open <url>           # Navigate to URL
agent-browser back                 # Go back
agent-browser close                # Close browser

# Snapshots (get element refs)
agent-browser snapshot -i          # Interactive elements with refs (@e1, @e2, etc.)
agent-browser snapshot -i --json   # JSON output

# Interactions (use refs from snapshot)
agent-browser click @e1            # Click element
agent-browser fill @e1 "text"      # Fill input
agent-browser type @e1 "text"      # Type without clearing
agent-browser press Enter          # Press key

# Screenshots
agent-browser screenshot out.png       # Viewport screenshot
agent-browser screenshot --full out.png # Full page screenshot

# Headed mode (visible browser)
agent-browser --headed open <url>      # Open with visible browser
agent-browser --headed click @e1       # Click in visible browser

# Wait
agent-browser wait @e1             # Wait for element
agent-browser wait 2000            # Wait milliseconds
```
