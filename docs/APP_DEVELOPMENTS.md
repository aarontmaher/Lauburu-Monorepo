# App developments — repo-backed roadmap

Single source of truth for the **active** roadmap Aaron carries
between the laptop terminal, ChatGPT chats, and the phone
Admin/Dev control centre. Apple Notes is now stale as a roadmap:
it is a human scratchpad only. Anything intended to drive work
must be promoted into this repo-backed roadmap / backlog flow.
The in-app Admin/Dev "Backlog" card mirrors this file. When the
file changes, the next paired build picks it up — no live-fetch
required yet (the long-term shape is the connector reading this
via the MCP route layer once Supabase is wired).

Status language used below:

| Tag | Meaning |
|---|---|
| **live** | Running in production / a deployed component (Worker, last released mobile build, etc.). |
| **repo-only** | Code / docs are on `main` but not yet shipped via a tester build, deployment, or dashboard step. |
| **tester-build** | Will ship to testers when the next paired Android v17 / iOS Build 18 dispatch goes (or whatever the next paired-build cadence is at the time). |
| **blocked** | Cannot move without a specific external action — Aaron's manual step, vendor processing window, or upstream dependency. |

Updated 2026-05-07.

## Active priority order

The MCP connector/control-centre path is **Priority 1** because
every other priority benefits from ChatGPT being able to read
Claude / Codex lane status without screenshots. The remaining
priorities keep their relative order below that app-control lane.

### 1. Screenshot-free MCP terminal bridge / control centre (Priority 1) — IN FLIGHT

ChatGPT and the mobile Admin/Dev surface should read Claude /
Codex lane status, build state, handoff, and recent terminal
summaries from one admin-token-gated read path — no Termius
screenshots, no manual paste, no raw terminal control.

Priority 1 has three inseparable pieces:

1. **ChatGPT-compatible MCP connector auth/read path** — the
   Worker exposes the MCP protocol and REST `/api/*` read routes,
   authenticated by the existing owner token.
2. **Screenshot-free terminal status** — the local bridge writes
   sanitized `coder_lanes`, `terminal_summary`, `handoff`, and
   `work_status` state without storing raw pane logs.
3. **App Admin/Dev status consumer** — the phone reads
   `EXPO_PUBLIC_MCP_BASE_URL` and renders owner-only status cards
   for Aaron.

| Component | Status |
|---|---|
| Cloudflare Worker (`lauburu-mcp-preview`) | **live** — `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/` |
| Worker admin-token gate | **live** — every connector route 403s without `x-athlete-memory-token` |
| Worker routes (`/api/work_status`, `/api/coder_lanes`, `/api/build_status`, `/api/handoff`, `/api/terminal_summary`) | **live** — placeholder + `dataSource.schemaRequired` payload until Supabase wires |
| MCP protocol endpoint (`POST /mcp`) | **live** — ChatGPT-compatible tool calls for the same five read objects |
| Local tmux bridge (`scripts/bridge-snapshot-lanes.sh` / `npm run bridge:snapshot`) | **live** — writes 4 sanitised JSON artifacts to `data/agent-status/lanes/` |
| Bridge artifact schema test (`npm run bridge:verify`) | **live** |
| Live worker integration test (`npm run mcp:test:live`) | **live** — 11/11 assertions pass |
| Express parity routes in `chat-app` | **live in repo** (chat-app is parity reference, not deployed) |
| Supabase migration `0003_connector_status_tables.sql` | **repo-only** — committed at `955bfed`, awaiting manual apply |
| Worker `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` secrets | **blocked** on Aaron's `wrangler secret put` after the migration |
| Mobile Admin/Dev cards reading the Worker | **tester-build** — `EXPO_PUBLIC_MCP_BASE_URL=<worker>/api` env switch + next paired build |
| Bridge → Supabase upsert (`LaneStatusWritePayload` consumer) | **repo-only / planned** — schema exists; producer code not yet written |

**Done flag for Priority 1:** Aaron taps an Admin/Dev card on the
phone and sees the live Claude lane summary written by the local
bridge to Supabase, fetched by the Worker, returned to the app
through `EXPO_PUBLIC_MCP_BASE_URL`.

### 2. Health / Data Source reliability

Real-tester functionality for Aaron's iPhone (Apple Health) and
his girlfriend's Android (Health Connect) is the first health
source target. Two devices in active daily use must connect
cleanly, surface what's available, and stay honest about what's
missing. Manual check-ins + training logs are the fallback when a
source isn't connected.

Hard guardrails (preserved):

- Apple Health is iOS-only; Health Connect is Android-only. No
  cross-platform claims.
- Missing data stays missing — never fabricated.
- No paid-tier gating for these two primary sources (already
  un-gated, commit `d4827ba`).

Status: **live** for the existing primary cards in last paired
build. Next moves are tester-build verifications, then source
expansion in this order:

1. Android Health Connect reliability.
2. Apple Health stability.
3. WHOOP Direct truthfulness / setup.
4. Polar / Bluetooth truthfulness.
5. Manual session logging.
6. Optional FIT / CSV import later.

Optional import backlog stays secondary: ErgZone FIT / CSV export
import, Concept2 Logbook indirect import, and Strava /
TrainingPeaks / Intervals.icu indirect import only when the user
already syncs there. Do **not** build ErgZone as a primary
dependency. These data-source lanes matter, but they do not
outrank the Apple Health / Health Connect daily testing path.

Generic conditioning import model:

- `sourceApp` — human-readable app label from Apple Health /
  Health Connect provenance when available.
- `sourceType` — `apple_health`, `health_connect`, `fit_file`,
  `tcx_file`, `csv_file`, or `manual`.
- `workoutType` — HIIT, rowing, ski erg, bike erg, assault bike,
  conditioning, or unknown.
- Timing — start time, end time, duration.
- Summary metrics — calories, distance, heart-rate summary when
  available.
- Intervals — present only when the source actually supplies
  structured interval splits; otherwise UI must say "Workout
  summary imported; interval splits not available."
- `provenanceLabel` — e.g. "ErgData via Health Connect"; never
  "Concept2 Direct", "ErgZone Direct", or "Rogue Direct" unless a
  verified direct integration exists.

### 3. UX / information architecture cleanup

Daily and frequent workflows live in the feature tabs where the
user naturally does that work. Rare settings, account state,
subscription, app version/build info, permissions, support,
diagnostics, and developer/admin controls live in Settings or
Admin/Dev.

Current rule:

- Health owns nutrition targets, source status, sync/storage
  actions, and health-source management.
- Train owns weekly schedule, training plans, and session
  logging.
- Settings is not a dumping ground. It should stay focused on
  account, subscription, version/build, notifications,
  permissions, support/feedback, and hidden Admin/Dev entry.

Status: **ongoing**. UX/IA stays after MCP bridge and
Health/Data Source reliability unless a tester-facing blocker is
urgent.

### 4. Cautious early Grappler Readiness prototype

Uses only available data (Apple Health / Health Connect + manual
check-ins + training logs) and clearly shows missingness. No
strong "you are ready" claims. Labelled provisional.

**Hard guardrail (preserved):** No Grappler Readiness UI ships
until Batches B / C / D land. Tonight's prototype work is
doc-only (`docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md`).

| Batch | What | Status |
|---|---|---|
| B | Extend `NextDayCheckin` sliders (soreness, mood, perceived fatigue) | repo-only / planned |
| C | Extend `TrainingSession` schema (gi/no-gi, drilling vs live, perceived intensity) | repo-only / planned |
| D | Bucket-ring UI on `AthleteStateStrip` (5 buckets with provenance) | repo-only / planned |

### 5. Admin/Dev workflow + Cloudflare / Supabase MCP bridge on the phone

The owner-workflow surface that lets Aaron manage everything from
the phone. Subsumes the previous "Railway read-only / MCP-style
bridge" priority. Railway is deprecated; Cloudflare Worker +
Supabase is the active replacement for connector/control-centre
state.

- Admin/Dev surface (Now / Android / iOS / OTA cards, Primary
  actions, Prompt bridge, Quick capture, Open shortcuts):
  **live**.
- Workflow buttons (typecheck, release audit, backend smoke,
  Android build + upload, iOS build + submit, OTA diagnostic):
  **live** — owner-tap only, never auto-dispatched.
- Mobile MCP endpoint switch (`EXPO_PUBLIC_MCP_BASE_URL`):
  **live in code** (commit `7e40763`); **tester-build** to
  flip on for testers.
- Cloudflare Worker: see Priority 1 above.

## Later backlog (not in the active top 5)

### 6. Paid AI API integration

Deferred until monetisation + usage caps + data readiness all
exist. Triggers documented in:

- `docs/AI_PROVIDER_STRATEGY.md`
- `docs/AI_MONETISATION_AND_USAGE_STRATEGY.md`

Hard guardrail: no paid AI API call until both trigger docs
explicitly say go. Status: **blocked** by design until then.

### 7. Public production release

Out of scope until the production listing pass is done (separate
from the now-complete Internal Testing pass). Status: **blocked**
on production listing pass.

### 8. Stage-5 local Mac / tmux bridge daemon

Phone taps a fixed allowlist of safe actions over Tailscale. Gate
is the eight hard rules in `docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md`
Stage 5. Stage 1 (the read-only producer) is **live**; the
write-side daemon stays **repo-only / planned**.

## Hard guardrails (apply across every priority)

These don't move without an explicit doc commit. They are not a
priority — they are the floor below every priority.

- **Apple Health iOS-only, Health Connect Android-only.** No
  cross-platform fallback.
- **Missing data stays missing.** No fabricated zeros, no
  invented connections.
- **No Grappler Readiness UI yet.** Doc-only until Batches B / C
  / D ship.
- **No paid AI API.** Gated on the two strategy docs.
- **Build dispatch is owner-tap only.** Connector / bridge cannot
  trigger builds.
- **EAS build cost control.** Do not run, trigger, recommend, or
  prepare a new EAS build unless all are true:
  1. Agent has completed a human-style app audit or targeted
     verification.
  2. Agent explicitly confirms the change is worthwhile to test
     on-device.
  3. The change is bundled with other meaningful mobile changes
     where possible.
  4. Typecheck/tests pass first.
  5. Aaron explicitly approves the build.
  Default is no EAS build, no tester build, no "quick build to
  check", no build for docs/backend/MCP-only changes, and no build
  for tiny copy/UI tweaks unless bundled. Use mobile typecheck,
  unit tests, local inspection, simulator/dev-client if already
  available, Admin/Dev MCP status, and Agent audit confirmation
  instead.
- **Admin/Dev gating preserved.** No tester sees admin surfaces
  or owner-only FABs.
- **No secrets / tokens in any committed file** — `.env*` are
  gitignored; bridge artifacts pass through the two-pass
  redactor; Worker / chat-app responses pass through the same
  redactor at the boundary.
- **Do not touch grappling.opml content** — off-limits.
- **Agent role boundary.** Agent work is app UX audit worker work
  only: observe screens, find clutter/regressions, and propose or
  patch small mobile UX fixes when explicitly assigned. Agent is
  not a backend deployer, not an MCP auth owner, not a Supabase
  operator, and not a build dispatcher.

## Top 5 priorities (the answer to "what's next")

In order:

1. **MCP connector/control-centre read path** — ChatGPT-compatible MCP auth/read path, screenshot-free terminal status, and app Admin/Dev status consumer. Apply `supabase/migrations/0003_connector_status_tables.sql` and set the two Worker secrets so the connector routes flip from `placeholder` to `supabase`.
2. **Health / Data Source reliability** — verify Apple Health on Aaron's iPhone + Health Connect on girlfriend's Android first; then continue WHOOP / Polar / exports / nutrition without blocking the primary daily sources.
3. **UX / IA cleanup** — keep daily/frequent workflows in feature tabs and rare/admin/config/debug in Settings/AdminDev unless an urgent tester blocker jumps the queue.
4. **Cautious Grappler Readiness Batches B / C / D** — architecture/schema + gated UI work only; no overclaiming and no user-facing readiness score until explicitly allowed.
5. **Admin/Dev → Cloudflare/Supabase MCP wiring on the phone** — flip `EXPO_PUBLIC_MCP_BASE_URL` in the next paired build's EAS env so the phone reads from the Worker, not Railway.

Items 6+ stay in the Later backlog above.

## Manual steps for Aaron (phone-first)

The only steps that genuinely need a human + browser. Everything
else is dispatchable from Admin/Dev.

1. **Apply the Supabase migration.** Open Supabase project
   `aarontmaher's Project` (`rejalrfmievikabgsakf`) → SQL Editor
   → paste `supabase/migrations/0003_connector_status_tables.sql`
   → Run. (Priority 1 unblocker.)
2. **Set the Worker secrets.** From the laptop:
   ```sh
   cd cloudflare-worker
   npx wrangler secret put SUPABASE_URL --name lauburu-mcp-preview
   # https://rejalrfmievikabgsakf.supabase.co
   npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY --name lauburu-mcp-preview
   # service_role JWT from Supabase → Settings → API
   npx wrangler deploy --env preview
   ```
3. **Verify.** `npm run mcp:test:live` should still pass and
   `dataSource.source` should flip from `placeholder` to
   `supabase` on every route.
4. **Tester device install** — TestFlight / Play Store auto-update
   once notified — no action needed beyond accepting the prompt.

## What's NOT in this file

- Long-form architecture (lives in `docs/architecture/`).
- Specific code TODOs (tracked in code, not here).
- Per-batch task breakdowns (in conversation history; this file
  carries the cross-conversation roadmap only).
- The grappling.opml content (untouched, off-limits).
- Old build / submission post-mortems — moved to
  `docs/BACKLOG_AUTOMATION_SYSTEM.md` and the relevant per-build
  audit docs.
