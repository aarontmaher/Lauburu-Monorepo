# WHOOP / Polar sync strategy

How direct sync (OAuth/API), historical export uploads, and
Health-Connect re-export paths fit together. Apple Health on iOS
and Health Connect on Android remain the **primary** product
surface; WHOOP and Polar are valuable secondary sources for users
who own the hardware.

Companion to `HEALTH_METRIC_APPS_DEVICES_AUDIT.md` (per-device
wearability + role) and `HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md`
(engineering state).

Updated 2026-05-06.

## Current source priority

1. Android Health Connect.
2. Apple Health stability.
3. WHOOP Direct truthfulness / setup.
4. Polar / Bluetooth truthfulness.
5. Manual session logging.
6. Optional FIT / TCX / CSV import later.

ErgZone is **not** a primary dependency. Keep it in backlog only as
an optional future import source:

- ErgZone FIT / TCX / CSV export import.
- Rogue / Concept2 Logbook indirect import.
- Strava / TrainingPeaks / Intervals.icu indirect import if the
  user already syncs there or provides a file export.

These import paths are backfill / history aids, not live source
claims and not requirements for the primary Health tab.

Generic conditioning import fields:

- `sourceApp`
- `sourceType`: `apple_health`, `health_connect`, `fit_file`,
  `tcx_file`, `csv_file`, or `manual`
- `workoutType`: HIIT / rowing / ski erg / bike erg /
  assault bike / conditioning / unknown
- start time, end time, duration
- calories, distance, heart-rate summary when available
- intervals only when the upstream source actually provides them
- provenance label such as "ErgData via Health Connect"

Apple Health / Health Connect imports are summary-first. If interval
splits are missing, the app must say: "Workout summary imported;
interval splits not available." Do not feed these summaries into
strong readiness claims yet.

## Two distinct paths per provider

For each of WHOOP and Polar there are TWO paths the app supports.
They surface in different places in the UI and carry different
trust levels:

| Path | Surface | Sync mode | Trust |
|---|---|---|---|
| **Connect (direct OAuth/API)** | Health → More sources → Connect button | live_sync — daily-ish freshness | High when working; primary intent |
| **Upload export file** | Health → More sources → Upload export | historical_upload — backfill only | Trustworthy for history, NEVER labelled live/current |

The labels are non-overlapping: "Connect WHOOP" never means
upload, "Upload WHOOP export" never means live. Mixing them is a
P1 product bug per `FEEDBACK_PRIORITY_MODEL.md` rule 4
(misleading health/readiness claim).

## WHOOP

### Connect (direct) — primary future path

OAuth scopes used (server-side, Railway env): `read:recovery`,
`read:cycles`, `read:sleep`, `read:workout`, `read:profile`,
`read:body_measurement`, `offline`. Implementation lives at
`chat-app/src/server/routes/integrations.ts` `/whoop/*`.

State today: `config_missing` / `auth_required` paths render
correctly. The dev-portal app registration is the upstream gap
that returns `404 Application not found` when the route is hit
without a registered redirect URI. The mobile UI now surfaces
"Coming soon" instead of raw 404 JSON (commit `a036fd5`).

When connected, fetched fields:
- `recovery_score` (0–100) — independent cross-check vs Lauburu
  Readiness's HRV/RHR/sleep_hours signals.
- HRV (RMSSD), resting HR.
- Day strain.
- Workouts (type, duration, average HR, max HR, kilojoules).
- Sleep stages + duration.
- Cycle metadata ("WHOOP day" definition).
- Profile + body measurements.

UI label rules:
- "WHOOP Direct" card under `More sources` in Health tab —
  member-gated as a richer secondary surface.
- StatusPill → `Connected` (green) when scored, `Awaiting today's
  cycle` when `partial && latestDay === today`, `Partial` (amber)
  when `partial && older`, `Stale` (yellow), `Reconnect required`
  (red) on auth error.
- Footer never says "live recovery score" — recovery is scored
  the morning after sleep ends, so the latest value is always
  yesterday-ish. UI says "Last cycle: {date}" not "Live".

### Upload export (raw / CSV) — historical backfill

Backend route: `POST /api/integrations/whoop/csv/{upload,upload-zip,clear}`
(plus `GET /whoop/csv/status`). Already live.

Trust: high for historical analysis (90+ days of cycles, sleep,
workouts), but never labelled live. The `whoop_csv_imported_v1`
secure-storage key tracks import status.

UI label rules:
- "Upload WHOOP export" surfaces in the Health-tab `More sources`
  disclosure — distinct button from `Connect WHOOP`.
- After import, the WHOOP card shows a "Imported · historical
  backfill" sub-line, never "Live".
- Coach answers reference imported data via `source_roles`
  including the `whoop_csv` layer separately from the live
  `whoop_direct` layer.

## Polar

### Connect (direct AccessLink) — planned

OAuth via Polar AccessLink — `chat-app/src/server/routes/integrations.ts`
`/polar/*` routes. Same `config_missing` / `auth_required`
pattern as WHOOP; same upstream gap (the AccessLink dev-portal
app needs registration, not in scope this lane).

When wired, fetched fields:
- Workouts (sport, duration, HR avg/max, zones, calorie estimate).
- R-R intervals (some firmwares) — would unlock independent HRV
  calc.
- Daily activity totals (steps, active calories) on devices with
  Polar Flow sync.

Polar **armband** (OH1, Verity Sense): mat-survivable. This is
the grappling-relevant Polar hardware. Direct sync from a paired
Polar Flow account brings the workout records.

Polar **chest strap**: NOT mat-survivable (slides under pressure,
buckle scrapes the partner). The app must not assume chest-strap
data is grappling data.

### Upload export (raw / TCX / CSV) — historical backfill

Parser: `packages/shared/src/backend/services/polar/parse-polar-export.ts`.
8MB cap, FIT not supported, CSV/TCX yes. Ingested via
`POST /api/athlete-memory/:athleteId/polar-export/import` with
dedupe by (athleteId, startTime, sport).

UI label rules: same as WHOOP — distinct button, "Imported ·
historical backfill" labelling, never live.

### Health Connect re-export (Android only)

When a user has Polar Flow installed on Android with
"Write to Health Connect" enabled, Polar workout + HR data
arrives via Health Connect provenance — surfaced as
`polar_via_health_connect` rather than `direct_polar`. This is a
second secondary path on Android only; on iOS, Apple Health does
not natively re-export Polar.

## Anti-rules

- Do not show WHOOP recovery score / Polar workout summary as
  PRIMARY product readiness. App-owned Lauburu Readiness +
  Grappler Readiness are product truth; WHOOP and Polar are
  evidence inputs only.
- Do not silently substitute WHOOP HRV when Apple Health HRV is
  missing, or vice versa. Each source has its own `availableFields`
  / `missingFields` view; the user sees both honestly.
- Do not expose raw backend errors to normal users. The friendly-
  error helper in `IntegrationCards.tsx` (commit `a036fd5`)
  normalises 404 / "Application not found" / network / auth /
  5xx errors into one user-safe sentence — or hides the line
  entirely when non-actionable.
- Do not claim "WHOOP CSV is live" or "Polar export is current".
  The historical_upload mode is explicit; Coach context flags
  imported data with its layer source so trend answers stay
  truthful.
- Do not ask users to install WHOOP / Polar apps if they don't
  already have them. Apple Health (iOS) and Health Connect
  (Android) are the primary path; WHOOP and Polar are richer
  secondary sources for users who own the hardware.

## Out of scope tonight

- Registering the WHOOP dev-portal app + Polar AccessLink app
  (Aaron-side, separate operational task).
- Direct Garmin / Oura — `HEALTH_METRIC_APPS_DEVICES_AUDIT.md`
  defers both; no integration tonight.
- R-R intervals from Polar TCX → HRV computation (deferred
  follow-up; armband data alone is enough for the first
  iteration).
