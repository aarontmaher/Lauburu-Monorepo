# Health connectivity — source-of-truth spec

The single doc that says, in one place, **what each health
provider can actually deliver into GrapplingMap today, what's
honest to claim about it, and what's allowed to feed Grappler
Readiness right now vs later.**

This doc is **spec only**. No implementation, no native BLE, no
mobile UI changes, no version bump, no EAS build. Code and UI
land in batches downstream of this spec, gated by the EAS build
cost control rule in `docs/BACKLOG_AUTOMATION_SYSTEM.md`.

Companion to:
- `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md` (per-source claim audit)
- `docs/HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md` (engineering state)
- `docs/WHOOP_DIRECT_SETUP.md` (WHOOP OAuth wiring)
- `docs/WHOOP_POLAR_SYNC_STRATEGY.md` (WHOOP/Polar paths + anti-rules)
- `docs/BLUETOOTH_MVP_SPEC.md` (BLE Train-session HR scope)
- `docs/NUTRITION_TRACKING_PLAN.md` (nutrition import)
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` (readiness compute spec)
- `docs/POST_MCP_PRODUCT_LANES.md` (Lane A health reliability,
  Lane B readiness UI gating)
- `docs/CONTROL_CENTRE_MVP_SPEC.md` (the iPhone surface that
  consumes the per-source state)

Updated 2026-05-07.

## 1. Provider classification

Per-provider state today. Status uses the canonical six-value
classification the prompt that requested this doc named, **plus**
an explicit "do not promote" flag where the truth-stickers below
require it.

| Provider | Status | Path | Notes |
|---|---|---|---|
| **Apple Health hub (iOS)** | live verified | iOS HealthKit primary card; aggregates from Apple Watch + any third-party app writing to HealthKit | un-gated from free tier (commit `d4827ba`); platform default for iOS testers; missing data stays missing |
| **Health Connect hub (Android)** | live verified | Android Health Connect primary card; aggregates from any registered source app | un-gated from free tier; platform default for Android testers; missing data stays missing |
| **Polar via hub** | live verified | Polar Flow → Apple Health (iOS) or Health Connect (Android) → Lauburu reads from the hub | data appears under the platform hub label, not "Polar". `friendlyDirectSyncError()` (commit `a036fd5`) handles the disconnect-vs-no-data distinction |
| **WHOOP direct (OAuth)** | partially wired | `chat-app/src/server/sources/liveWhoopReader.ts` + Supabase `source_connection_state` row + `WHOOP_DIRECT_SETUP.md` setup | OAuth callback was anchored to Railway URLs (`docs/WHOOP_DIRECT_SETUP.md` line 14); Railway is deprecated. **Migration off Railway disk to Supabase encrypted token storage is repo-only / planned**. |
| **Polar direct (OAuth / API)** | planned only | `WHOOP_POLAR_SYNC_STRATEGY.md` § "Polar" | reserved label `Polar Direct`; **MUST NOT** be marked live in any UI / source label / connector response until the OAuth wiring + token storage land |
| **WHOOP raw export** | app-side ready | manual upload of WHOOP CSV / zip to `/admin/manual-import` | `manual_imports` Supabase table accepts the shape; parser version flagged |
| **Bluetooth HR sensor (HRS, GATT 0x180D)** | planned only | `BLUETOOTH_MVP_SPEC.md` Phase 1 native scaffold + Phase 3+ pairing UI | Train-session data ONLY; never feeds readiness in the MVP |
| **Generic conditioning imports** | app-side ready | `manual_imports` (CSV / ad-hoc) — same envelope as WHOOP raw export | parser routing TBD per `NUTRITION_TRACKING_PLAN.md` for shape; conditioning-specific subset not yet documented |
| **Manual check-in / training log** | live verified | `NextDayCheckin` + `TrainingSession` (existing schemas) | Train tab; no backend integration needed; the readiness compute already accepts these |
| **Garmin / Oura / Whoop-via-BLE** | NOT supported | — | out of scope per `WHOOP_POLAR_SYNC_STRATEGY.md` anti-rules |

## 2. Source matrix — per metric × per provider

**What each metric source can deliver today.** Cells use the
truth labels in § 3. Empty cell = provider does not deliver this
metric, or it's explicitly out of scope (e.g. WHOOP doesn't
expose nutrition; BLE HRS doesn't expose sleep).

| Metric | Apple Health hub | Health Connect hub | Polar via hub | WHOOP direct | Polar direct | WHOOP export | BLE HR sensor | Manual / log |
|---|---|---|---|---|---|---|---|---|
| HR (live) | live (Apple Watch) | live (HC source app) | synced from hub | setup required | planned | imported summary | planned | — |
| HR (resting) | live | live | synced from hub | setup required | planned | imported summary | — | — |
| HRV | live | live | synced from hub | setup required | planned | imported summary | — | — |
| Sleep duration / stages | live | live | synced from hub | setup required | planned | imported summary | — | — |
| Recovery / readiness (vendor-native) | — (Apple Health doesn't expose Apple's "training load" as recovery) | — | — | setup required (vendor-native) | planned | imported summary (numeric) | — | — |
| Strain / load (vendor-native) | — | — | — | setup required (vendor-native) | planned | imported summary | — | manual perceived intensity (live) |
| Workout / training session | live | live | synced from hub | setup required | planned | imported summary | — | live (Train tab `TrainingSession`) |
| Active calories | live | live | synced from hub | setup required | planned | imported summary | — | — |
| Nutrition | imported summary (Apple Health "Nutrition" types) | imported summary (HC nutrition) | — | — | — | — | — | live (manual + planned `NUTRITION_TRACKING_PLAN.md`) |
| Generic conditioning import | — | — | — | — | — | imported summary (CSV) | — | imported summary (CSV) |

**Reading the matrix:**

- "live" means data is currently flowing into the app and
  rendered without seed/provisional flagging.
- "synced from hub" means the data IS live, but it appears
  under the platform-hub label, NOT under the vendor's name.
- "imported summary" means the data lands as an aggregate
  (daily / weekly), not real-time.
- "setup required" means code exists; vendor OAuth or token
  setup pending.
- "planned" means doc-only.

## 3. Truth labels (canonical strings)

These six labels are the only allowed phrasings for any UI
chip, source label, MCP response, or connector text describing
a metric's source. Coders MUST NOT invent shorter / longer
phrasings; consumers can pattern-match.

| Label | When to use | Example |
|---|---|---|
| `live` | Data is reading in real-time; rendering without provisional flags. | "Apple Health hub: live" |
| `synced from hub` | Vendor data is reaching the app, but via the platform hub. The vendor itself is not directly connected. | "Polar via hub: synced from hub" |
| `imported summary` | Aggregated upload (CSV / zip / vendor-native daily summary). Per-event timing is not preserved. | "WHOOP export: imported summary" |
| `seed/provisional` | Reading exists but should be treated as low-confidence (insufficient sample, recently connected, or sensor known to be noisy). UI shows a `provisional` chip. | "WHOOP direct: seed/provisional" |
| `setup required` | Code path exists; user / owner action needed before the source goes live. | "WHOOP direct: setup required (Aaron OAuth pending)" |
| `planned` | Doc-only. No reading, no code path. | "Polar direct: planned" |

`live verified` / `live` are the same end-state for the user;
the audit-side distinction lives in
`HEALTH_METRIC_APPS_DEVICES_AUDIT.md`.

## 4. What's allowed to feed Grappler Readiness now

The Grappler Readiness compute lives in
`packages/shared/src/backend/services/readiness/grappler-readiness.ts`.
Per `docs/POST_MCP_PRODUCT_LANES.md` Lane B, no Grappler
Readiness UI ships until Lane A (Apple Health / Health Connect
reliability) holds AND Aaron approves Batches B / C / D. This
section names the input contract for that compute.

### Allowed input today (low-risk readiness inputs)

- Apple Health hub (iOS): RHR, HRV, sleep duration. **`live`** label only.
- Health Connect hub (Android): RHR, HRV, sleep duration. **`live`** label only.
- Manual check-in (`NextDayCheckin`): subjective fatigue / mood / soreness sliders (Batch B extension). **`live`** label.
- Training session (`TrainingSession`): grappling minutes, drilling vs live (Batch C extension). **`live`** label.

### NOT allowed input today (do-not-promote-yet)

- WHOOP direct vendor-native recovery / strain — labelled
  `seed/provisional` until the OAuth-off-Railway migration
  ships AND Aaron has 4+ weeks of WHOOP data flowing.
- Polar direct anything — labelled `planned`; readiness compute
  MUST NOT branch on it.
- Bluetooth HR sensor live HR — Train-session data only per
  `BLUETOOTH_MVP_SPEC.md`. Readiness compute MUST NOT consume
  BLE-derived HR points.
- Imported summary (any provider) — readiness must not equate
  an imported summary with a `live` continuous signal.
- Generic conditioning imports — out of scope for readiness;
  these feed the conditioning history / load surface, not the
  recovery/strain buckets.

### Readiness output rule (mirrors `GRAPPLER_READINESS_PROTOTYPE_PLAN.md`)

Every readiness reading rendered to the user MUST carry:

- A confidence chip: `provisional` (default), `confidence: low`,
  `confidence: medium`. `confidence: high` is reserved.
- A per-bucket provenance line naming the source (e.g.
  `apple_health` / `health_connect` / `whoop_oauth` /
  `polar_oauth` / `manual` / `missing`). When `missing`, the
  bucket renders grey with the literal label "no data".
- Never a strong `you are ready` claim. Hedge language only.

## 5. Do-not-promote-yet list

Mirror of `BLUETOOTH_MVP_SPEC.md` § 6 + readiness gating, kept
here so a future audit doesn't re-open them as candidate work
on the health-connectivity surface.

- **WHOOP direct as `live`** — stays `setup required` until
  the Railway-disk → Supabase-encrypted token migration ships
  AND Aaron's WHOOP data has flowed for ≥7 days without auth
  drops.
- **Polar direct anywhere** — label reserved; do NOT use
  `Polar Direct`, `Polar API`, or any vendor-direct phrasing
  in UI / source labels / connector responses.
- **Bluetooth HR sensor as readiness input** — never; Train-
  session data only.
- **Garmin** — out of scope; no integration path.
- **Oura** — out of scope.
- **WHOOP-via-BLE** — WHOOP doesn't expose a public BLE HRS
  profile.
- **Hub-aggregated data labelled as the vendor** — Polar data
  arriving via Apple Health is `synced from hub`, never
  "Polar live".
- **`live` label without verification** — coders MUST NOT mark
  any new source `live` without an explicit test on Aaron's
  iPhone AND girlfriend's Android.
- **Strong readiness claims without direct source data** — no
  `you are ready` / `train hard today` strings unless the
  readiness compute has at least one `live`-labelled recovery
  bucket on the day in question.

## 6. MCP / Admin-Dev health status fields

The fields the Cloudflare Worker / `/api/control_centre` /
`/mcp/v2` SHOULD expose so the iPhone Admin/Dev surface can
render honest health status. None of these are implemented in
this spec commit; they are the contract for a later batch.

### `connector_health_sources` (proposed Phase 3 table)

Stores per-source connectivity state, sanitised. NOT athlete
private memory.

```sql
-- supabase/migrations/0005_connector_health_sources.sql (PLANNED)
create table if not exists public.connector_health_sources (
  source text primary key check (
    source in ('apple_health_hub', 'health_connect_hub',
              'polar_via_hub', 'whoop_oauth', 'polar_oauth',
              'whoop_export', 'ble_hr_sensor',
              'generic_conditioning_import', 'manual_log')
  ),
  status text not null check (
    status in ('live', 'synced_from_hub', 'imported_summary',
              'seed_provisional', 'setup_required', 'planned')
  ),
  last_sync_at timestamptz,
  /** counts only — no per-user / per-record values */
  recent_record_count int,
  /** sanitised — no raw error message, no token, no user_id */
  last_error_category text check (
    last_error_category is null
    or last_error_category in ('auth', 'rate_limit', 'shape',
                               'network', 'permission')
  ),
  generated_at timestamptz not null,
  updated_at timestamptz not null default now()
);
```

### MCP exposure

A new tool surface in `cloudflare-worker/src/mcp-v2.ts`:

| Tool | Auth | Returns |
|---|---|---|
| `integrations.get_health_sources` | No Auth (counts/aggregates only) | per-source `{ source, status, lastSyncAt, recentRecordCount, lastErrorCategory }` — every field strict-allow-listed |
| `integrations.get_health_source` (admin-token) | admin | full row including the 5 above + a sanitised one-line summary (≤140 char) |

**Privacy constraint:** even the admin-gated detail tool MUST
NOT include raw token text, user identifiers, athlete metric
values, vendor-side error messages, or HR/HRV samples.
`recentRecordCount` is the only numeric volume signal allowed.

### `/api/control_centre` `liveStatus` extension (proposed)

Add a `healthSources` sub-object to the existing
`liveStatus` block:

```ts
liveStatus: {
  android: { … existing fields },
  ios:     { … existing fields },
  repo:    { … existing fields },
  healthSources: {  // NEW
    apple_health_hub:           { status: 'live' | …, lastSyncAt: string | null },
    health_connect_hub:         { status: …, lastSyncAt: … },
    polar_via_hub:              { status: …, lastSyncAt: … },
    whoop_oauth:                { status: …, lastSyncAt: … },
    polar_oauth:                { status: …, lastSyncAt: … },
    whoop_export:               { status: …, lastSyncAt: … },
    ble_hr_sensor:              { status: …, lastSyncAt: … },
    generic_conditioning_import:{ status: …, lastSyncAt: … },
    manual_log:                 { status: …, lastSyncAt: … }
  }
}
```

Render rule: if the Admin/Dev Control Centre shows
`liveStatus.healthSources.<src>.status` and the value is one of
`{ setup_required, planned }`, the chip MUST be amber, not
green. `live` and `synced_from_hub` get green. `seed_provisional`
gets amber. `imported_summary` gets a neutral colour.

### EAS build cost control (mirror)

Spinning up a tester build solely to verify a health source
state change is **NOT permitted** under the EAS build cost
control rule (`docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build
cost control rule"). Verification flow:

1. Run `npm run mcp:test:v2-live` against the deployed Worker.
2. Read `integrations.get_health_sources` from the laptop curl
   path or via ChatGPT's unified MCP connector.
3. Bundle any health-source UI change with other meaningful
   mobile changes per the bundling rule.
4. Coder reports
   `Implementation-complete, awaiting Agent functional confirmation`
   when typecheck/tests pass; never `fully complete`.

## 7. Build-readiness wording for health changes

When a coder implements a health-source change (Apple Health
permission UX, Health Connect declaration, WHOOP token storage
migration, etc.), the report MUST use the four-status sequence
from `BACKLOG_AUTOMATION_SYSTEM.md`:

`Implementation-complete, awaiting Agent functional confirmation`
→ `Agent-confirmed, ready for Aaron build approval`
→ `Aaron-approved for EAS build`
→ `Built/tester-ready`

Coders MUST NOT call a health-source change `fully complete`,
`done`, or `shipped` until Aaron has tested on his iPhone AND
girlfriend has tested on her Android (where applicable). "Done"
in this codebase means tester-device verified.

## 8. Anti-rules

- **No vendor-direct claim without verification.** Until WHOOP
  OAuth migration off Railway ships AND tokens are flowing
  cleanly, every WHOOP UI MUST say `setup required` or
  `seed/provisional`, never `live`.
- **No Polar direct labels anywhere.** Reserved.
- **No readiness UI on top of unreliable data.** Lane B waits
  on Lane A (`POST_MCP_PRODUCT_LANES.md`).
- **No EAS build to verify a health-source state change.**
  Verify via MCP / curl / typecheck per § 6.
- **No raw athlete metric values in any MCP / control-centre
  response.** Counts and status enums only at the unauth
  layer; admin-gated tools may add sanitised summaries but
  never per-record values.
- **No tokens, user IDs, or vendor-side error messages in any
  source state.** Sanitised category enums only.
- **No coder-side "live" promotion.** A source moves from
  `setup required` / `seed/provisional` to `live` only via
  Aaron's tested-on-device approval, recorded in
  `docs/FEEDBACK_SUGGESTIONS.md` per the candidate workflow.

## 9. Codex handoff prompt

Use this prompt verbatim when the next health-connectivity
implementation batch is ready. Phase 3 of the schema-and-MCP
work below is the practical first batch.

```
PROMPT-ID: CODEX-HEALTH-SOURCES-MCP-FIELDS-PHASE-1-DOCS-AUDIT-01
TYPE: CODEX
LANE: Mobile / health source state surface
PRIORITY: Make Admin/Dev iPhone show truthful per-source status

Source of truth: docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md.

Phase 1 (this batch): docs / mobile audit ONLY. NO migration,
NO Worker route addition, NO native rebuild, NO version bump.

Do:
1. Read docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md § 1, 2, 3, 5, 7.
2. Audit apps/mobile/app/(tabs)/health.tsx (or current Health
   tab entry) and report which existing source labels match
   the canonical truth labels (live / synced from hub /
   imported summary / seed/provisional / setup required /
   planned). Flag any phrasing that needs to be brought into
   line.
3. Audit apps/mobile/src/services/* for any "Polar Direct" or
   vendor-direct WHOOP-as-live string. Flag and propose
   replacement to "setup required" or "synced from hub".
4. Confirm the four-status build-readiness wording is followed
   for any health-related FS-XXX candidate in
   docs/FEEDBACK_SUGGESTIONS.md.
5. NO React UI implementation in this batch. NO Worker code.
   Audit and doc patches only.
6. Bundle any small phrasing fix with the next mobile batch
   (do NOT spin a build for a copy fix per the EAS build cost
   control rule).
7. tsc --noEmit clean in apps/mobile if any patches land.

Output:
- changed files (docs / small mobile copy patches only)
- list of mismatched source labels found
- list of any "Polar Direct" / vendor-direct violations
  flagged
- four-status wording compliance per FS-XXX candidate
- recommendation for Phase 2: build the
  connector_health_sources Supabase migration + Worker
  integrations.get_health_sources tool
- committed yes/no
```

## 10. Out of scope for this spec commit

- BLE implementation (covered by `BLUETOOTH_MVP_SPEC.md`).
- WHOOP OAuth token migration off Railway disk (separate
  Lane-3 batch; service-role rotation involved).
- Polar direct OAuth wiring (`planned` only).
- Native rebuild / EAS build dispatch.
- Mobile UI changes (Codex's lane).
- Schema migration `0005_connector_health_sources.sql` —
  proposed shape lives in § 6 only; the actual migration file
  lands when the Phase-2 batch ships.
- Any Grappler Readiness UI work (gated on Lane B per
  `POST_MCP_PRODUCT_LANES.md`).

## 11. Cross-references

- `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md` § "Per-source
  detail" — the long-form per-provider audit.
- `docs/HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md` § "Snapshot
  table" — engineering state.
- `docs/WHOOP_DIRECT_SETUP.md` — WHOOP OAuth + Railway
  callback setup (note: callback URL is Railway-anchored;
  migration to Cloudflare Worker is a separate Lane-3 batch).
- `docs/WHOOP_POLAR_SYNC_STRATEGY.md` § "Anti-rules" — anti-
  rules already preserved here in § 8.
- `docs/BLUETOOTH_MVP_SPEC.md` § 6 — BLE do-not-promote list
  mirrored.
- `docs/POST_MCP_PRODUCT_LANES.md` Lane A + Lane B — gating
  for health reliability + readiness UI.
- `docs/CONTROL_CENTRE_MVP_SPEC.md` `liveStatus` block —
  where the proposed `healthSources` sub-object slots in.
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build cost
  control rule" — applies to every health-source UI change.
