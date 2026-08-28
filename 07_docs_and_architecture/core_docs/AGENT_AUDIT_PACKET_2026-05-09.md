# Agent audit packet — 2026-05-09

Persistent, audit-ready packet of the work shipped on `main`
between commits `58c821a` and `7193ee1`. Provided so a blocked
Agent audit (MCP stale, no_writeback, terminal truth ahead of
worker writeback) can read the evidence directly from the repo
without scrolling chat history.

This packet is repo-only. **No installed-device verified claim.**
**No EAS / TestFlight / Play upload.** **No production release.**

## Commits in scope

| SHA | Headline |
|---|---|
| `58c821a` | UI: dark-premium theme tokens + 8 design primitives |
| `d4a6e02` | UI: migrate Manage Sources `SourceSheetRow` to `SourceChip` primitive |
| `a0c9816` | HealthConnect: register app for permissions (rationale intent-filter + `requestPermission` flow + did-not-register state pill) |
| `9f3143a` | AdminDev: fix iPhone MCP-unavailable (URL double-append) + safe diagnostics + app-resume refresh |
| `e51d179` | AdminDev: add lane progress strip (status / age / fresh-stale-unknown badge / progress bar / next-prompt) |
| `3cba259` | QA: Android v21 retest readiness bundle (prebuild manifest test + Admin/Dev build-state separation + v21 checklist) |
| `dd4f8c8` | Rules: add Rule 1 (MCP-first + terminal-truth fallback + no idle lanes) at id 24 |
| `7193ee1` | OvernightQueue: schema + idle-lane recommendation + public/admin redaction + Admin/Dev surface |

## 1. Health Connect Android registration (`a0c9816`)

### Manifest / native config

`apps/mobile/plugins/withAndroidHealthConnectPermissionDelegate.js`
adds, idempotently:

- 8 `<uses-permission>` entries (already present pre-patch):
  `READ_HEART_RATE`, `READ_HEART_RATE_VARIABILITY`,
  `READ_RESTING_HEART_RATE`, `READ_STEPS`,
  `READ_ACTIVE_CALORIES_BURNED`, `READ_SLEEP`, `READ_EXERCISE`,
  `READ_HEALTH_DATA_HISTORY`.
- `<intent-filter>` on `MainActivity` with
  `<action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE"/>`
  (Android 13- compat — already present).
- **NEW** `<activity-alias>` block (the actual fix):

  ```xml
  <activity-alias android:name=".ViewPermissionUsageActivity"
                  android:exported="true"
                  android:targetActivity=".MainActivity"
                  android:permission="android.permission.START_VIEW_PERMISSION_USAGE">
    <intent-filter>
      <action android:name="android.intent.action.VIEW_PERMISSION_USAGE"/>
      <category android:name="android.intent.category.HEALTH_PERMISSIONS"/>
    </intent-filter>
  </activity-alias>
  ```

`MainActivity.kt` retains:
`import dev.matinzd.healthconnect.permissions.HealthConnectPermissionDelegate`
+ `HealthConnectPermissionDelegate.setPermissionDelegate(this)` in
`onCreate`.

### Prebuild output verified

`npx expo prebuild --platform android --no-install --clean` ran
2026-05-09 against the patch. The rendered
`apps/mobile/android/app/src/main/AndroidManifest.xml` contains
all of the above. `MainActivity.kt` contains the delegate
import + `setPermissionDelegate(this)` call.
`cloudflare-worker/test/test-android-prebuild-manifest.ts` locks
the markers (skips silently when `android/` is absent — it is
gitignored).

### Connect calls `requestPermission` first

`apps/mobile/src/components/HealthActionsPanel.tsx`
`onConnectHealthConnect`:

1. Audit event `permission_requested`.
2. **Calls `requestPermissions()` first** (the store-level call
   that routes through `health.android.ts` → `mod.requestPermission(HC_PERMISSIONS)`).
3. Reads back the resulting permission state.
4. Audit event `permission_granted` or `permission_denied`.
5. If granted + signed in: runs `syncData(user.id)` immediately.
6. **Only if denied** does it offer a secondary "Open Health
   Connect" Alert button that calls `openHealthConnectSettings`.

`cloudflare-worker/test/test-android-health-connect-crash-guard.ts`
static-checks the call order: the first occurrence of
`requestPermissions(` precedes the first occurrence of
`openHealthConnectSettings` within the function body.

### Fallback UI when the app remains unlisted

`apps/mobile/src/store/health-store.ts` exposes
`hcRegistrationStatus: 'unknown' | 'registered' | 'did_not_register'`.
The probe lives in `apps/mobile/src/services/health.android.ts`
as `didLastPermissionRequestFailToRegister()`: zero grants
returned in <250 ms with SDK still reporting available is
treated as "OS never showed the dialog".

`apps/mobile/src/components/HealthActionsPanel.tsx` renders the
new status string `'Health Connect did not register'` on the
Health Connect source row when the probe reports the failure
mode. Mapped through
`apps/mobile/src/components/primitives/source-status-mapper.ts`
to canonical `'setup required'` (no new TruthLabel — anti-rule
preserved). Meta hint: "Health Connect did not register the
app — open Health Connect → Apps and verify Lauburu Grappling
Map appears, then tap Retry permission request." Primary action
label switches from `Connect` to `Retry permission request`.

### Package + label visible to Health Connect

- Package: `com.lauburu.grapplingmap` (`apps/mobile/app.json`
  `android.package`).
- Label: "Lauburu Grappling Map" (`apps/mobile/app.json` `name`)
  — Expo wires this into AndroidManifest's `android:label`
  automatically.

### Tests

| Test | Status | Locks |
|---|---|---|
| `cloudflare-worker/test/test-android-health-connect-crash-guard.ts` | ✅ | plugin source + `health.android.ts` probe + UI markers + Connect-before-Settings call order |
| `cloudflare-worker/test/test-android-prebuild-manifest.ts` | ✅ | rendered AndroidManifest + MainActivity.kt contain HC registration markers |
| `cloudflare-worker/test/test-source-sheet-status-mapper.ts` | ✅ | 'Health Connect did not register' → 'setup required'; 12 legacy strings → canonical TruthLabels |

### New Android build required

**Yes.** The manifest fix only ships when `expo prebuild` runs
as part of a new EAS build. v20 cannot retest with the
activity-alias.

### v21 retest path

Authoritative checklist + Aaron retest steps in
`docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` § "Android v21 retest
readiness bundle (2026-05-09)".

## 2. iPhone Admin/Dev MCP transport (`9f3143a`)

### Root cause

`EXPO_PUBLIC_MCP_BASE_URL` shipped to v19 was the full
`<root>/mcp/v2` URL. Two clients re-appended path suffixes:

- `apps/mobile/src/services/mcp-v2-client.ts` re-appended
  `/mcp/v2` → `…/mcp/v2/mcp/v2` (404 → "MCP current-state
  unavailable").
- `apps/mobile/src/services/connector-status-client.ts`
  re-appended `/api` → `…/mcp/v2/api/*` (404 → empty connector
  snapshot, lanes 0, Rule 12 not loaded).

ChatGPT MCP works because its connector URL ends at `/mcp/v2`
and never re-appends.

### Patch

- `apps/mobile/src/services/ai-backend-config.ts` exports
  `mcpWorkerRootUrl()` + pure `normaliseMcpWorkerRootUrl()`
  that strips the longest known suffix
  (`/mcp/v2/admin`, `/mcp/v2/website`, `/mcp/v2/health`,
  `/mcp/v2`, `/mcp/core`, `/mcp/public`, `/api`). Reads
  `process.env` on every call.
- Both clients now route through `mcpWorkerRootUrl()` and
  append exactly one path.

### Safe diagnostics surface

`McpV2DashboardSnapshot` gains `resolvedCoreEndpoint`,
`resolvedAdminEndpoint`, `envSource: 'mcp' | 'public_backend' |
'unconfigured'`, `fetchDurationMs`, and
`diagnostics: McpV2CallDiagnostics[]` with categorical reason
(`'ok' | 'transport' | 'rpc_error' | 'no_content' |
'parse_error' | 'mcp_base_url_missing'`) + HTTP status per call.
**No tokens, raw bodies, or stack traces.**

### App-resume refresh

`apps/mobile/app/admin-dev.tsx` adds an
`AppState.addEventListener('change', …)` subscription that
calls `refresh()` on `'active'`. Listener subscribes once on
mount; reads the latest `refresh` via a ref.

### Tests

| Test | Status | Locks |
|---|---|---|
| `cloudflare-worker/test/test-mcp-worker-root-url.ts` | ✅ | 15 static + 4 env-lookup cases; idempotent under repeat normalisation; the `/mcp/v2/mcp/v2` regression cannot recur |

## 3. Admin/Dev lane progress strip (`e51d179`)

### Pure summariser

`apps/mobile/src/services/lane-progress-summary.ts`. Per-lane
shape (per Rule 1 / file § rule 24):

- `id`, `status` (lower-cased)
- `ageMs`, `ageLabel` (compact: `<1s` / `Ns` / `Nm` / `Nh` / `Nd` / `—`)
- `freshness: 'fresh' | 'stale' | 'unknown'` — **stale wins
  over per-lane fresh** (snapshot-stale veto)
- `idleStatus: 'working' | 'idle' | 'stale' | 'blocked' |
  'needs_user' | 'needs_review' |
  'complete_waiting_approval' | 'unknown'`
- `needsPrompt: boolean`
- `progressPct: number | null` (null → "unknown" verbatim;
  never coerced to 0%)
- `recommendedNextPrompt: string | null`
- `recommendedNextPromptTarget: string` (defaults to lane id)
- `recommendedNextPromptSummary: string | null` (≤140 chars)
- `taskSummary: string | null`

`LaneProgressSummary` exposes `promptsRequired` —
the Rule 1 enforcement payload. UI must render every entry as
an immediate "queue a prompt" affordance.

### UI

`apps/mobile/app/admin-dev.tsx` — "Lane progress" chip block
in the Now section (after the Live marker writeback chip,
before the Lane heartbeat chip). Each row: lane id, status +
age, fresh/stale/unknown badge, progress bar (filled or
"progress unknown" track), "Next: …" line.

The Rule 1 banner (`dd4f8c8`) renders above the strip when
`promptsRequired.length > 0`. Stale cached `working` MUST
NEVER suppress this banner — terminal-idle override flips
`idleStatus` to `'idle'`.

### Tests

| Test | Status | Locks |
|---|---|---|
| `cloudflare-worker/test/test-lane-progress-summary.ts` | ✅ | fresh / stale / unavailable / unknown-progress / Rule 1 idle-prompt routing / terminal-truth override / all-idle-statuses |

## 4. Build-state separation + v21 readiness (`3cba259`)

### Build-state separation

New "Build state separation" chip block in Admin/Dev. Per
platform: `Android — installed-build verified (vN)` (green
`verified` badge) when installed === target;
`Android — repo-only patch ahead of installed (installed vN
→ target vM)` / `Android — repo-only (target vN not installed)`
(neutral `repo-only` badge) otherwise. Same shape for iOS.
**Default state is `repo-only` until a real installed-device
run flips it.**

### v21 retest readiness

`docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` § "Android v21 retest
readiness bundle (2026-05-09)" — 9-item pre-flight checklist
with evidence pointers + 12 numbered Aaron retest steps + anti-
rules.

## 5. Rule 1 — no idle lanes (`dd4f8c8`)

### Operating rule

Added at id=24 (high id keeps prior 1..23 cross-references
stable; the title carries priority). Doc preamble adds "Read
rule 24 first".

`docs/OPERATING_RULES.md` § rule 24: TOP-PRIORITY pre-flight
rule fusing rule 11 (MCP-first), rule 19 (coordinator-fed idle
lanes), and a new terminal-truth fallback clause. Every
status reply, audit, or project message MUST satisfy:

1. Check MCP first; report `freshness.isStale`,
   `freshness.staleReason`, `updatedAt` exactly.
2. Treat terminal truth as authoritative when MCP is stale
   or contradicted by terminal evidence. Stale cached
   `working` MUST NEVER suppress an idle-lane prompt.
3. Every idle / blocked / needs_user / needs_review /
   complete_waiting_approval lane gets a recommended next
   prompt in the same response.
4. MCP / control-centre payload contract: per lane,
   `laneFreshness`, `idleStatus`,
   `recommendedNextPromptTarget`, `recommendedNextPromptText`,
   `recommendedNextPromptSummary`, `promptProgressPercent`
   (0..100 integer or `null` / `'unknown'`).
5. UI rendering contract: progress 'unknown' renders
   verbatim; missing recommendations render `'queue a prompt'`,
   not blank.
6. Hard-floor exceptions: rules 7 (EAS cost), 21 (human
   approval), 22 (AI spend), 23 (deep research) remain
   floors no recommended-next-prompt may bypass.

### Tests

| Test | Status |
|---|---|
| `cloudflare-worker/test/test-rule-1-no-idle-prompt.ts` | ✅ — locks the rule's title position, body markers, and idle-lane summariser behavior |
| `cloudflare-worker/test/test-operating-rules.ts` | ✅ — 24 rules, ids 1..24 |

## 6. Overnight Prompt Queue MVP (`7193ee1`)

### Schema

`cloudflare-worker/src/overnight-queue.ts` defines the
`connector_overnight_queue` row contract verbatim from the
spec (id / title / lane_owner / runtime_minutes /
requires_human_interaction / safe_overnight / dependencies /
interrupt_priority / repo_only_relevance /
preview_only_relevance / installed_build_verified_relevance /
suggested_execution_window / progress_pct / outcome_summary /
created_at / updated_at / started_at / completed_at;
stale_age_hours computed at read time).

### Helpers

- `validateOvernightRow` — row-level structural validation.
- `pickRecommendedTask` — priority-ordered FIFO selection
  with dependency gating; never re-recommends in-flight tasks.
- `recommendOvernightTaskForLane` — idle-lane auto-routing
  that returns null when ANY P0 or P1 is pending for the lane
  (P0/P1 ALWAYS win; queue is secondary).
- `buildPublicOvernightQueueSummary` — public-safe summary
  (count + recommended task id + safe-to-run flag + stale
  flag). Never carries row content.
- `redactOvernightRowForAdmin` — admin redaction (title
  truncated, dependencies replaced with count,
  outcome_summary capped at 140 chars).

### MCP / control-centre additions

- `project.get_current_state.overnightQueue` field shape:
  `{ count, recommendedTaskId, safeToRunUnattended,
  hasStaleEntries }` — public-safe.
- `project.list_overnight_queue` admin tool returning
  `AdminOvernightRow[]` — to be wired in `mcp-v2.ts` once
  the Supabase migration lands.

### UI

`apps/mobile/app/admin-dev.tsx` — new "Overnight queue" admin
chip block in the Now section. Reads
`mcpCurrentState.overnightQueue` (gracefully empty when MCP
has not yet started emitting the field). Recommendation only —
Aaron approves before any overnight execution.

### Tests

| Test | Status |
|---|---|
| `cloudflare-worker/test/test-overnight-queue.ts` | ✅ — 9 cases: schema validation, FIFO within priority, P0 + P1 override, dependency gating, in-flight skip, stale flagging, admin redaction, public summary key set integrity, empty queue |

### Remaining blocker

Supabase `connector_overnight_queue` migration + worker adapter
wiring (`fetchOvernightQueueRows`) + `mcp-v2.ts` integration to
populate `project.get_current_state.overnightQueue` — gated on
Aaron's schema-change approval.

## Aggregate test sweep (all green on `main` HEAD)

```
npx tsx cloudflare-worker/test/test-android-prebuild-manifest.ts          ✅
npx tsx cloudflare-worker/test/test-android-health-connect-crash-guard.ts ✅
npx tsx cloudflare-worker/test/test-source-sheet-status-mapper.ts         ✅
npx tsx cloudflare-worker/test/test-mcp-worker-root-url.ts                ✅
npx tsx cloudflare-worker/test/test-lane-progress-summary.ts              ✅
npx tsx cloudflare-worker/test/test-rule-1-no-idle-prompt.ts              ✅
npx tsx cloudflare-worker/test/test-overnight-queue.ts                    ✅
npx tsx cloudflare-worker/test/test-ui-primitives-helpers.ts              ✅
npm run rules:test                                                         ✅ (24 rules)
npm run mcp:test:public-redaction                                          ✅ (4 tools, 10 patterns)
cd apps/mobile && npx tsc --noEmit                                         ✅
```

## Anti-rules respected across every commit

- No EAS build, TestFlight upload, Play upload, or production
  release.
- No installed-device verified claim. Every UI badge that could
  imply verified state defaults to `repo-only` until a real
  installed-device run flips it.
- Truth labels preserved through the canonical eight
  `TruthLabel` strings in
  `apps/mobile/src/components/primitives/_helpers.ts`.
- Stale wins over fresh (snapshot-stale vetoes per-lane fresh).
- Diagnostics never expose tokens, raw bodies, or stack traces.
- Health meaning, readiness math, source truth semantics
  unchanged.
- Hard-floor exceptions to Rule 1: rules 7, 21, 22, 23.

## Agent decision needed

Whether the four batches (HC registration, MCP transport fix,
lane progress strip + Rule 1 banner, overnight queue MVP) +
the prebuild evidence are sufficient to flip the v20 audit
from "needs patch / more evidence" to **patched, awaiting
v21 installed-device retest** — and to queue v21 EAS
approval to Aaron. The "verified" badge in the build-state
separation panel is the canonical signal Agent should flip
its audit from "patched, awaiting retest" to "verified" only
after Aaron records an installed-device pass via
`npm run bridge:agent-qa`.
