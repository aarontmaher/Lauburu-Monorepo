# Admin/Dev Control Centre — implementation-ready MVP spec

A single screen on the iPhone that answers "what's happening with
the project right now?" without screenshots, terminal access, or
Apple Notes. Reads from the Cloudflare Worker, which composes
one `ControlCentreSnapshot` from the existing connector tables
plus two small additions.

This doc is the spec. **No React UI implementation in this
batch.** No Worker route added yet. The scope here is: schema,
composition, missing tables, screen layout, acceptance criteria,
phone test checklist, implementation phases.

Companion to:
- `docs/MCP_PHONE_CONTROL_CENTRE.md` (live MCP read paths)
- `docs/CONNECTOR_SUPABASE_SCHEMA.md` (envelope + safety model)
- `docs/APP_DEVELOPMENTS.md` (active priorities)
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` (three-lane risk model)

Updated 2026-05-07.

## 1. Snapshot schema

One JSON object served by `GET /api/control_centre` (Phase 1
adds this route). All free-text fields pass through the
existing two-pass redactor before serialisation. Status labels
use the four-value enum from `APP_DEVELOPMENTS.md`:
`live` / `repo-only` / `tester-build` / `blocked`.

```ts
interface ControlCentreSnapshot {
  schemaVersion: 1;
  /** ISO Z. The most recent timestamp across the four input tables. */
  updatedAt: string;
  /** ISO Z. When the Worker assembled this response. */
  generatedAt: string;

  /**
   * Single-glance connection state for the Status Banner. Always
   * non-null. Values:
   *   'connected'  — Worker reachable AND every connector_* read
   *                  returned a row (`dataSource.source === 'supabase'`
   *                  on every input route) AND data is fresh
   *                  (`updatedAt` within the freshness window).
   *   'stale'      — Worker reachable; some/all reads succeeded
   *                  but `updatedAt` is older than the freshness
   *                  window. UI shows an amber chip + "stale Xm ago".
   *   'fallback'   — Worker reachable but at least one upstream read
   *                  returned `dataSource.source === 'placeholder'`
   *                  (table empty / Supabase env unset). UI shows a
   *                  red chip with the placeholder reason.
   *   'offline'    — Network fetch failed; phone rendered the last
   *                  cached snapshot. Set by the mobile client, not
   *                  the Worker.
   */
  mcpConnectionStatus: 'connected' | 'stale' | 'fallback' | 'offline';
  /** Default freshness window: 10 minutes. Beyond this →
   *  mcpConnectionStatus = 'stale'. */
  freshnessWindowMs: number;

  /** What is currently being worked on. */
  priority: ControlCentreCard;
  /** What's stopping the priority. Null when nothing blocks. */
  blocker: ControlCentreCard | null;
  /** Single actionable next step. */
  nextAction: ControlCentreCard;

  /** One row per coder lane the bridge has seen. */
  lanes: ControlCentreLane[];

  /** Mobile build / store-pipeline state. */
  buildDeploy: ControlCentreBuildDeploy;

  /** Things only Aaron can do. Most recent first; cap 10. */
  manualSteps: ControlCentreManualStep[];

  /** Single top item from the structured backlog. Null when empty. */
  topBacklog: ControlCentreBacklogItem | null;

  /** Pointer to the prompt library entries the phone can copy/paste. */
  promptLibrary: ControlCentrePromptRef[];
}

interface ControlCentreCard {
  /** Free text, ≤280 chars, redacted. */
  text: string;
  /** UI badge label. */
  status: 'live' | 'repo-only' | 'tester-build' | 'blocked';
  /** ISO Z. Source row's updated_at. */
  updatedAt: string;
}

interface ControlCentreLane {
  laneId: 'claude' | 'codex' | 'claude_chat' | 'chatgpt' | 'cowork';
  status: 'idle' | 'working' | 'blocked' | 'needs_user' | 'needs_review' | 'done';
  /** Compressed summary, ≤140 chars, redacted. Suitable for one card line. */
  oneLine: string;
  /** ISO Z. Null when the lane has never been seen. */
  lastSeenAt: string | null;
  /** True when currentPromptId is set (lane is mid-work). */
  hasOpenPrompt: boolean;
}

interface ControlCentreBuildDeploy {
  android: {
    versionCode: number | null;
    /** Highest-priority status enum across github/play. */
    status: 'live' | 'repo-only' | 'tester-build' | 'blocked';
    /** Free text, ≤120 chars, redacted. */
    lastChange: string;
    updatedAt: string;
  };
  ios: {
    buildNumber: string | null;
    status: 'live' | 'repo-only' | 'tester-build' | 'blocked';
    lastChange: string;
    updatedAt: string;
  };
}

interface ControlCentreManualStep {
  /** Stable id (UUID v7 or generated text). */
  id: string;
  /** Free text, ≤200 chars, redacted. */
  text: string;
  category: 'supabase' | 'cloudflare' | 'eas' | 'play_console' | 'app_store_connect' | 'github' | 'other';
  /** True when the step is high-risk and gates the rest of the priority. */
  blocking: boolean;
  /** Lane-3 items per BACKLOG_AUTOMATION_SYSTEM.md. */
  approvalRequired: boolean;
  approval: 'pending' | 'approved' | 'completed' | 'declined';
  createdAt: string;
  updatedAt: string;
}

interface ControlCentreBacklogItem {
  id: string;
  /** ≤120 chars, redacted. */
  title: string;
  /** 1–11 ladder per IN_APP_DEV_BACKLOG_PLAN.md. Lower = higher priority. */
  priority: number;
  status: 'live' | 'repo-only' | 'tester-build' | 'blocked';
  type:
    | 'bug' | 'ux_issue' | 'feature_idea' | 'release_blocker'
    | 'health_data_issue' | 'ai_coaching_idea'
    | 'monetisation_payment_idea' | 'railway_backend_issue'
    | 'source_integration_issue';
  riskLevel: 'low' | 'medium' | 'high';
  needsBuild: boolean;
  updatedAt: string;
}

interface ControlCentrePromptRef {
  id: string;
  /** ≤80 chars. Plain title, never the prompt body. */
  title: string;
  /** Stable enum the mobile prompt-template generator already exposes. */
  templateId: string;
}
```

## 2. Worker composition

Phase 1 adds `GET /api/control_centre` (admin-token-gated). The
handler composes the snapshot in one pass without writing
anywhere. Pseudocode:

```ts
async function buildControlCentreSnapshot(env: Env) {
  const now = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) return placeholderSnapshot(env, now);

  const [workRow, lanesRows, buildRow, handoffRow, manualRows, backlogRow] =
    await Promise.all([
      adapter.fetchSingleRowPayload('connector_work_status'),
      adapter.fetchCoderLaneRows(),
      adapter.fetchSingleRowPayload('connector_build_status'),
      adapter.fetchSingleRowPayload('connector_handoff'),
      adapter.fetchManualSteps(),       // NEW (see § 3)
      adapter.fetchTopBacklogItem(),    // NEW (see § 3)
    ]);

  return {
    schemaVersion: 1,
    generatedAt: now,
    updatedAt: maxIsoZ([
      workRow?.generatedAt, buildRow?.generatedAt, handoffRow?.generatedAt,
      ...lanesRows.map(r => r.payload.lastSeenAt),
    ]),
    priority: cardFromWorkStatus(workRow, 'priority'),
    blocker: cardFromWorkStatus(workRow, 'blocker'),
    nextAction: cardFromWorkStatus(workRow, 'nextAction'),
    lanes: lanesRows.map(rowToControlCentreLane),
    buildDeploy: composeBuildDeploy(buildRow),
    manualSteps: manualRows.map(rowToManualStep),
    topBacklog: backlogRow ? rowToBacklogItem(backlogRow) : null,
    promptLibrary: STATIC_PROMPT_LIBRARY,
  };
}
```

Mapping rules:

- **priority / nextAction** → `connector_work_status.payload.currentPriority`
  / `nextAction`. Status label derived: `'blocked'` when blocker is
  non-null; otherwise `'live'`. Future iterations can pull
  per-priority status from a richer field.
- **blocker** → `connector_work_status.payload.currentBlocker`. Null
  when missing. Status always `'blocked'` when present.
- **lanes** → `connector_coder_lanes` rows. `oneLine` is
  `truncate(payload.lastSummary, 140)` after the redactor; if
  empty, fallback to `${laneId}: ${status}`. `hasOpenPrompt` is
  `payload.currentPromptId !== null`.
- **buildDeploy.android.status / .ios.status** → derived from the
  payload's GitHub / Play / TestFlight status enums:
  - `failure` / `failed` / `invalid_binary` → `blocked`
  - `submitted_completed` / `available` / `rolled_out` → `live`
  - `submitted_draft` / `uploaded_processing` / `success` (build
    workflow only) → `tester-build`
  - everything else → `repo-only`.
- **buildDeploy.\*.lastChange** → free-text summary, e.g.
  `"v17 / Build 18 — Play submission complete; TestFlight
  processing"`. Generated server-side; cap 120 chars; redactor
  applied.
- **manualSteps** → `connector_manual_steps` (NEW). Most recent
  first by `updated_at`; cap 10.
- **topBacklog** → `connector_backlog_items` (NEW),
  `where status != 'done' order by priority asc limit 1`.
- **promptLibrary** → static const inside the Worker; not from
  any table. The mobile app already owns the bodies via
  `apps/mobile/src/services/prompt-templates.ts`; the snapshot
  surface only carries titles + template ids so the phone can
  resolve.

Sanitisation: every string field passes through the existing
two-pass redactor at the response boundary. The `dataSource`
discriminator from the underlying routes is collapsed: a single
top-level `dataSource: 'supabase' | 'placeholder'` field tells
the consumer whether all four upstream tables backed the
response or any fell through.

## 3. Missing Supabase tables

**Tables needed: yes — two new tables.** Manual steps and
backlog items have richer structure than fits cleanly inside
the existing `connector_handoff` envelope; promoting them to
their own tables makes the bridge / owner-tap write paths
explicit.

These get a separate migration `0004_control_centre_tables.sql`
in the next batch (NOT in this docs-only commit). Spec:

```sql
-- 0004_control_centre_tables.sql (Phase 2, NOT yet committed)

create table if not exists public.connector_manual_steps (
  id uuid primary key default gen_random_uuid(),
  scope text not null default 'default',
  text text not null check (char_length(text) <= 200),
  category text not null check (
    category in ('supabase', 'cloudflare', 'eas', 'play_console',
                'app_store_connect', 'github', 'other')
  ),
  blocking boolean not null default false,
  approval_required boolean not null default false,
  approval text not null default 'pending' check (
    approval in ('pending', 'approved', 'completed', 'declined')
  ),
  source text not null default 'owner',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.connector_manual_steps is
  'Owner/control-centre manual steps. NOT athlete private memory.';
create index if not exists connector_manual_steps_recent
  on public.connector_manual_steps (updated_at desc);
alter table public.connector_manual_steps enable row level security;

create table if not exists public.connector_backlog_items (
  id uuid primary key default gen_random_uuid(),
  scope text not null default 'default',
  title text not null check (char_length(title) <= 120),
  priority int not null check (priority between 1 and 11),
  status text not null check (
    status in ('live', 'repo-only', 'tester-build', 'blocked', 'done')
  ),
  type text not null check (
    type in ('bug', 'ux_issue', 'feature_idea', 'release_blocker',
            'health_data_issue', 'ai_coaching_idea',
            'monetisation_payment_idea', 'railway_backend_issue',
            'source_integration_issue')
  ),
  risk_level text not null check (risk_level in ('low', 'medium', 'high')),
  needs_build boolean not null default false,
  source text not null default 'owner',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.connector_backlog_items is
  'Owner/control-centre backlog. NOT athlete private memory.';
create index if not exists connector_backlog_items_open_priority
  on public.connector_backlog_items (priority asc, updated_at desc)
  where status != 'done';
alter table public.connector_backlog_items enable row level security;
```

**Approval state:** lives inline on `connector_manual_steps.approval`.
No separate table needed for the MVP; promote later if approval
audit history matters.

**Existing tables that need NO change:**
`connector_work_status`, `connector_coder_lanes`,
`connector_build_status`, `connector_handoff`,
`connector_terminal_summary`. The snapshot reads them as-is.

## 4. iPhone screen layout

Single scrollable screen at Admin/Dev → Control Centre. All
sections are read-only in the MVP (no taps mutate Supabase yet
— Phase 4 adds the "mark step completed" write path).

```
┌────────────────────────────────────────┐
│ [Status Banner]                        │
│                                        │
│  MCP: [connected | stale | fallback |  │
│        offline] · last update Xm ago   │
│                                        │
│  PRIORITY                              │
│   <priority.text>                      │
│   • <priority.status badge>            │
│                                        │
│  BLOCKER (only if non-null)            │
│   <blocker.text>                       │
│   • blocked                            │
│                                        │
│  NEXT ACTION                           │
│   <nextAction.text>                    │
│   • <nextAction.status badge>          │
│                                        │
│  generatedAt: <relative time>          │
├────────────────────────────────────────┤
│ [Lane Cards]                           │
│                                        │
│  ▢ claude       [working]    2m ago    │
│   <lane.oneLine>                       │
│                                        │
│  ▢ codex        [idle]       11m ago   │
│   <lane.oneLine>                       │
│                                        │
│  (≤5 lanes; tap card → no-op in MVP)   │
├────────────────────────────────────────┤
│ [Build / Deploy]                       │
│                                        │
│  Android v<versionCode> · [status]     │
│   <android.lastChange>                 │
│  iOS Build <buildNumber> · [status]    │
│   <ios.lastChange>                     │
├────────────────────────────────────────┤
│ [Manual Steps]                         │
│                                        │
│  ◯ <step.text>                         │
│    <category badge> [approval state]   │
│  ◯ ...                                 │
│                                        │
│  (cap 10; section hidden if 0 steps)   │
├────────────────────────────────────────┤
│ [Backlog Preview]                      │
│                                        │
│  Top: <topBacklog.title>               │
│   priority <n> · <type> · <status>     │
│   risk <riskLevel>                     │
│                                        │
│  (link "open full backlog" → existing  │
│   in-app backlog screen)               │
├────────────────────────────────────────┤
│ [Prompt Library]                       │
│                                        │
│  • Claude prompt                       │
│  • Codex prompt                        │
│  • ChatGPT status prompt               │
│  • Terminal-check prompt               │
│  (resolves via existing                │
│   prompt-templates.ts on the device)   │
├────────────────────────────────────────┤
│ [Refresh] (manual fetch)               │
└────────────────────────────────────────┘
```

Header behaviour:

- Status Banner is the only section that's always visible.
- Refresh button calls `GET /api/control_centre` with the admin
  token. No background polling in MVP.
- Offline / fetch fail → show last successful snapshot with a
  "stale, last refreshed Xm ago" badge; do not fabricate data.
- 403 from the Worker → show "Token misconfigured. Set
  EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN and rebuild." inline; never
  prompt for the token in-app.

## 5. Acceptance criteria

A snapshot lands on the phone correctly when ALL of the
following are true:

1. **Reachable.** `GET /api/control_centre` returns HTTP 200 with
   `application/json` from
   `https://lauburu-mcp-preview.lauburu-aaron.workers.dev` when
   the admin token is present; HTTP 403 without it.
2. **Schema valid.** Response matches the TS interface above —
   verified by a tsx test (`test-control-centre-route.ts` —
   added in Phase 1).
3. **Latency.** p95 ≤ 500 ms server-side under steady load
   (six PostgREST reads + composition).
4. **Truthful.** Every status badge is one of the four enum
   values. No badge is empty, no field is `undefined`, every
   ISO timestamp parses.
5. **Sanitised.** No string field contains a JWT, an
   `sk-…` / `ghp_…` / `whsec_…` / `xox…` shape, or an
   absolute filesystem path. The redactor self-test still
   passes (`test-bridge-artifacts.ts` shape).
6. **Length-capped.**
   `priority.text` ≤ 280, `blocker.text` ≤ 280,
   `nextAction.text` ≤ 280, `lane.oneLine` ≤ 140,
   `manualStep.text` ≤ 200, `backlog.title` ≤ 120,
   `buildDeploy.*.lastChange` ≤ 120.
7. **Provenance.** Every section's `updatedAt` is the source
   row's `updated_at`, not `now()`.
8. **Owner-only.** Every UI section is rendered behind the
   existing Admin/Dev gate (`isAdminEmail(user)` already in
   the codebase). No tester sees this screen.
9. **Stable when partial.** With `connector_manual_steps`
   empty, the Manual Steps section hides cleanly; with
   `connector_backlog_items` empty, `topBacklog === null` and
   the Backlog Preview shows a one-line "no items" placeholder.
10. **No writes in MVP.** The screen reads only. Marking a
    manual step completed lands in Phase 4.

## 6. Phone test checklist

Tester walkthrough on Aaron's iPhone after Phase 3 ships:

- [ ] Open the app, sign in, tap Admin/Dev tab. Control Centre
      is the first thing visible.
- [ ] Status Banner shows priority text + status badge. Pull
      to refresh; timestamp updates.
- [ ] Blocker section is hidden when blocker is null; visible
      with red badge when non-null. (Force the latter by
      writing a `currentBlocker` value in
      `connector_work_status.payload`.)
- [ ] Lane Cards show ≥1 lane. Each card has lane id, status
      badge, oneLine summary, "Xm ago" relative time.
- [ ] Build/Deploy card shows Android versionCode + iOS
      buildNumber matching the seed in
      `connector_build_status`.
- [ ] Manual Steps card shows ≤10 entries. Each has category
      badge + approval state. Section hidden when 0 entries.
- [ ] Backlog Preview shows the top item by priority. "Open
      full backlog" link navigates to the existing in-app
      backlog screen.
- [ ] Prompt Library lists the four standard prompt
      titles. Tapping a title copies the resolved prompt body
      to the clipboard (resolves via
      `prompt-templates.ts`, NOT via the Worker).
- [ ] Force airplane mode → screen still shows the last
      cached snapshot with "stale Xm ago" badge.
- [ ] Toggle airplane mode off + Refresh → snapshot updates.
- [ ] Force a 403 (set
      `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN=wrong-value` in a dev
      build) → inline error message, no in-app token prompt.
- [ ] Sign out → Admin/Dev tab is hidden again (existing
      admin-email gate behaviour).

## 7. Implementation phases

| Phase | What | Lane | Status |
|---|---|---|---|
| 0 | This spec doc. | Lane 1 (docs) | DONE in this commit. |
| 1 | Add `GET /api/control_centre` Worker route + composition logic + tsx integration test. No new tables — placeholder when manual_steps / backlog tables are missing. | Lane 2 (build autopilot) | NEXT BACKEND BATCH |
| 2 | Apply `0004_control_centre_tables.sql` (manual_steps + backlog_items). Seed via Supabase MCP. Worker switches from placeholder to real on those two sections. | Lane 3 (DB migration; owner-approved) | After Phase 1 |
| 3 | Mobile UI: Admin/Dev → Control Centre screen. Read-only. Reads via existing `MCP_BASE_URL` + admin token. Owner-only via `isAdminEmail`. No version bump. | Lane 2 (Codex's lane) | After Phase 2 |
| 4 | Add `POST /api/control_centre/manual_steps/:id/approve` + write path so phone can mark steps completed. Lane 3 in BACKLOG_AUTOMATION_SYSTEM.md (write path). | Lane 3 | After Phase 3 ships to testers |
| 5 | Optional: approval-state audit history table. Currently inline on `connector_manual_steps.approval`. Promote when audit retention matters. | Lane 3 | Deferred |

## 8. Out of scope for the MVP

- Live polling / push from Worker to phone. The MVP refreshes
  on tap.
- Build dispatch from inside the Control Centre screen. Stays
  in the existing Admin/Dev → Primary actions surface.
- Editing the backlog or priorities from the phone. Owner taps
  in the existing in-app backlog editor; Control Centre only
  shows the top item.
- Per-prompt body display. Prompt Library shows titles only;
  the body is generated locally on tap by
  `apps/mobile/src/services/prompt-templates.ts` per Stage 3 of
  `LOCAL_BRIDGE_WORKFLOW_PLAN.md`.
- Auto-sync of `apps/mobile/src/store/owner-backlog-store.ts`
  with `connector_backlog_items`. Stays one-way (Supabase →
  phone read) until Phase 4.

## 9. Anti-rules

- **No raw terminal text in the snapshot.** `lane.oneLine` is a
  redacted, ≤140-char compression. Full
  `connector_terminal_summary` rows stay on the private
  `/api/terminal_summary` endpoint.
- **No new public surface.** All Control Centre routes are
  admin-token-gated. The public-safe `/mcp/public` preview at
  `docs/MCP_PHONE_CONTROL_CENTRE.md` § "Path A" is a separate
  product; it does NOT expose Control Centre data.
- **No third-party network calls from the Worker.** Cloudflare →
  Supabase only. No GitHub API, no Play Console API, no EAS
  API in this surface (build_status comes pre-aggregated from
  the existing release-workflow seed, not from live API calls).
- **No autosync from `apps/mobile`.** The phone reads; the
  laptop writes (bridge upsert + owner taps). Mobile state is
  cache, never source.
