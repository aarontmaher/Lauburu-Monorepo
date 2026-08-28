# In-app audit system

How the app captures structured "what is the health-source state
right now" events so Aaron and the connector can reason over the
real device behaviour without sending raw health data anywhere.

Companion to `HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md` (per-source
engineering state) and `RAILWAY_CONNECTOR_TOOLS.md` (read tool
spec).

Updated 2026-05-06.

## Principle

Audit events are **metadata about the source's state**, not the
data itself. The audit captures:

- "Apple Health card was visible on this iOS device."
- "Health Connect was unavailable — `getSdkStatus` returned
  `SDK_UNAVAILABLE`."
- "Permission for HRV was denied by the user."
- "Sync attempt completed; 0 records returned for steps."

The audit does NOT capture:

- Step counts.
- HRV ms values.
- Sleep durations.
- Workout details.
- Any user health time series.

That separation is load-bearing — it lets the audit travel through
backend routes without inheriting the privacy weight of raw health
data. Raw health data continues to live in the device-resident
HealthKit / Health Connect stores and the Supabase `normalized_
daily_metrics` rows the user owns.

## AuditEvent type

```ts
export type AuditEventType =
  | 'health_source_visible'
  | 'health_source_missing'
  | 'permission_requested'
  | 'permission_denied'
  | 'permission_granted'
  | 'sync_started'
  | 'sync_succeeded'
  | 'sync_failed'
  | 'missing_metrics'
  | 'backend_error_hidden'
  | 'raw_error_exposed'
  | 'feedback_submitted';

export type AuditSeverity = 'info' | 'warning' | 'error';

export type AuditSourceId =
  | 'apple_health'
  | 'health_connect'
  | 'whoop_direct'
  | 'polar_direct'
  | 'whoop_csv'
  | 'polar_export'
  | 'manual_checkin'
  | 'manual_training_log'
  | 'ble_machine';

export type AuditPlatform = 'ios' | 'android' | 'web' | 'unknown';

export type AuditStatus =
  | 'new'
  | 'triaged'
  | 'fixed_repo_only'
  | 'shipped'
  | 'verified'
  | 'archived';

export interface AuditEvent {
  id: string;
  createdAt: string;            // ISO timestamp
  userId?: string | null;       // anon when not signed in
  testerId?: string | null;     // distinct from userId for tester cohorts
  platform: AuditPlatform;
  appVersion?: string | null;   // e.g. "0.1.0"
  buildNumber?: string | null;  // e.g. "16" / "15" (versionCode on Android)
  screen?: string | null;       // e.g. "(tabs)/health"
  eventType: AuditEventType;
  severity: AuditSeverity;
  sourceId?: AuditSourceId | null;
  sourceState?: string | null;     // free-form short label
  permissionState?: string | null; // 'authorized' | 'denied' | 'not_determined' | …
  syncMode?: 'live_sync' | 'historical_upload' | 'manual' | 'unavailable' | null;
  lastSyncedAt?: string | null;
  availableFields?: string[];   // e.g. ['hr', 'rhr', 'steps']
  missingFields?: string[];     // e.g. ['hrv', 'sleep_duration']
  staleReason?: string | null;
  userVisibleMessage?: string | null;
  developerMessage?: string | null;
  screenshotUrl?: string | null;   // when paired with feedback attachment
  status: AuditStatus;
}
```

Hard rules per field:

- `userId` / `testerId` — only when the user is signed in. Anon
  events store both as `null`.
- `availableFields` / `missingFields` — list of metric KEYS, not
  values. Never include numeric data.
- `developerMessage` — for owner triage. May contain HTTP status
  codes, error categories, never tokens or PII.
- `screenshotUrl` — when an event is created from feedback that
  carries an attachment, the URL is the existing
  `/api/feedback/attachments/:filename` path (admin-gated).

## Local-first capture

Implementation lives at
`apps/mobile/src/store/audit-event-store.ts`. Events are
persisted to `secureStorage` under `lauburu_audit_events_v1`.
Capped at the most recent N=200 events on the device.

Reading is local-only by design — even when a backend route
lands, the app keeps the local ring as the canonical short-term
buffer so the device can render Admin/Dev → Audit without a
network call.

## Where capture sites land (this batch and follow-ups)

This batch:

- Adds the type definitions + the local store.
- Adds an Admin/Dev "Audit" section that reads the local store
  and renders the most recent events.

Follow-up batches (each one a small lane):

1. Capture `health_source_visible` on Health-tab mount per
   platform (Apple Health on iOS, Health Connect on Android).
   Helps confirm Build 16 / v15 actually exposed the un-gated
   primary card.
2. Capture `permission_requested` / `permission_denied` /
   `permission_granted` from `services/health.ios.ts` +
   `services/health.android.ts` request paths.
3. Capture `sync_started` / `sync_succeeded` / `sync_failed` +
   the failure-category enum from the same services.
4. Capture `backend_error_hidden` whenever
   `friendlyDirectSyncError()` returns `null` (commit `a036fd5`).
5. Capture `raw_error_exposed` if any UI ever renders a non-
   normalised backend error string — guard rail to catch
   regressions of the WHOOP / Polar fix.
6. Capture `feedback_submitted` on every `tester-feedback.ts`
   submit, with the audit event linking to the feedback record's
   ID + screenshot URL.

## Backend route contract (deferred — documented only)

Future routes (NOT in this batch). All shapes will follow
`CONNECTOR_SECURITY_MODEL.md` invariants — no raw health data,
no secrets, no PII beyond what's already in the feedback
records.

```
POST /api/audit/health-event
  Body: AuditEvent (server stamps id + createdAt if absent)
  Auth: shared `x-athlete-memory-token` for owner-only events;
        public callers (testers) submit via /api/feedback which
        the backend then derives an audit event from per
        IN_APP_DEV_BACKLOG_PLAN.md Option A.

GET /api/athlete-memory/admin/health-audit-summary
  Auth: requireAdminToken
  Returns: aggregated counts per { eventType, sourceId,
           severity, status } for the last 7 days, plus the most-
           recent N (≤25) events. Per-event detail returned
           without `userId` / `testerId` unless filter
           parameters explicitly include them and the JWT
           ownership cross-check passes.

GET /api/athlete-memory/admin/health-source-status
  Auth: requireAdminToken
  Returns: a roll-up of the latest per-source state across the
           cohort (count of devices showing healthy vs missing
           per source). NEVER returns per-user values.
```

When these land, they sit alongside `/admin/work-status` and the
mobile `Admin/Dev` Audit section also fetches them so Aaron sees
both his device's local events AND the cohort summary.

## Connector access

Per `CONNECTOR_BACKLOG_TOOLS_PLAN.md` second-wave write tools:

- `mark_audit_event_triaged` — same shape as
  `mark_feedback_triaged`. Owner-only, audit-logged.
- `get_health_audit_summary` — read-only roll-up.

The connector NEVER reads raw `AuditEvent` rows that contain a
`userId` / `testerId` other than Aaron's. The
`/health-audit-summary` route filters identifiers out before
serialising to the wire.

## Privacy boundary

Audit records are honest about source-state but inherently carry
some PII (the `userId` field, indirectly the user's app version /
device platform). Treatment:

- Local store is on the user's own device under `secureStorage`
  — same protection as the existing OAuth tokens.
- Admin/Dev → Audit section is owner-gated by the same email
  allowlist + dev-unlock that gates the rest of Admin/Dev.
- Backend routes (when they land) require `requireAdminToken`
  for read; tester writes go through `/api/feedback` (already
  privacy-reviewed) and the backend derives the audit event.
- Connector reads return roll-up counts without per-user
  identifiers by default.

## Out of scope for tonight

- Backend route implementation (contract documented; routes
  scaffold in a follow-up batch).
- Wiring all capture sites (this batch lands the type + local
  store + Admin/Dev card; capture sites land per the numbered
  follow-up list above).
- Cross-device cohort aggregation in Supabase (future).
- Sending audit data through any paid AI API (gated by
  `AI_PROVIDER_STRATEGY.md`).
