# Health source implementation audit

What's actually wired today, what's UI-only, what's repo-only,
what needs the next paired build, and what's spec-only. Companion
to `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md` (which carries the
device-and-claim story); this file is the **engineering** state.

Updated 2026-05-06.

## Snapshot table

| Source | Platform | State | Sync mode | Backed by | Next implementation step | Priority |
|---|---|---|---|---|---|---|
| Apple Health | iOS only | LIVE | live_sync (foreground) | `services/health.ios.ts` + `store/health-store.ts` | Add background-delivery wake-up so daily totals refresh on app open without manual tap | P1 |
| Health Connect / Android Health | Android only | LIVE | live_sync (foreground) | `services/health.android.ts` + `store/health-store.ts` | Verify SpO2 / skin temp on Galaxy Watch + Pixel Watch where Health Connect publishes | P1 |
| WHOOP Direct (OAuth) | both | LIVE | live_sync (cycle / sleep / recovery / strain / workouts) | `store/whoop-store.ts` + backend `routes/integrations.ts` `/whoop/*` | Surface `last-3-days` domain freshness in UI when today's cycle has only strain (already wired backend; verify on Build 16) | P1 |
| WHOOP CSV / raw upload | both | LIVE | historical_upload (backfill only) | backend `routes/integrations.ts` `/whoop/csv/{upload,upload-zip,clear,status}` | Confirm UI labels every row "Imported · backfill" not "Live" | P2 |
| Polar Direct (AccessLink OAuth) | both | LIVE | live_sync | backend `routes/integrations.ts` `/polar/*` | Confirm `direct_polar` source attribution distinct from `polar_via_health_connect` (Android Health Connect re-export) | P2 |
| Polar export / raw upload | both | LIVE | historical_upload | `services/parse-polar-export.ts` (in shared) + `routes/athleteMemory.ts` `/:athleteId/polar-export/import` | Limit upload size + dedupe by (athleteId, startTime, sport) — both already wired; verify | P3 |
| HIIT / conditioning logs | both | LIVE | manual + live machine (BLE FTMS / CPS / CSC / HR / Echelon) | `services/ble-connect.ts` + `store/hiit-workout-store.ts` + `app/(tabs)/train.tsx` | CPS subscription added (commit `a6c7079`); ride next paired build | P1 |
| Manual training session logs | both | LIVE | manual | `store/training-store.ts` + `app/(tabs)/train.tsx` | Extend with grappling-specific fields (gi/no-gi, drilling vs live, perceived intensity) — Grappler Readiness Batch C | P2 |
| NextDayCheckin (subjective) | both | UI only — minimal slider set | manual | `store/training-store.ts` (next-day-checkin slice) | Extend sliders for soreness / mood / perceived fatigue — Grappler Readiness Batch B | P2 |
| Nutrition (manual + barcode + Apple Health dietary) | both (iOS richer) | LIVE | manual + live (HealthKit dietary on iOS) | `store/nutrition-store.ts` + `services/health.ios.ts` `fetchDietaryDailyTotals` | Android Health Connect dietary read still pending — Health Connect schema is limited; manual entry primary on Android | P3 |
| Cronometer | both | repo-only scaffold | (unwired) | backend `routes/integrations.ts` `/cronometer/{status,import}` exists | Mobile UI not wired; no need until Aaron has a Cronometer cohort | P4 |
| Concept2 PM5 | both | LIVE — FTMS half via BLE | live_sync (session) | `services/ble-connect.ts` (FTMS_SERVICE catches PM5's FTMS half) | Proprietary PM5 protocol (pace / strokes / split) — follow-up | P3 |
| Samsung Health Direct | Android | scaffold | unwired in app today | `services/samsung-health-direct.ts` + `store/samsung-health-store.ts` | Galaxy users get Samsung Health → Health Connect re-export already, so Direct is low-value; defer | P4 |
| DEXA scan upload | n/a | spec only | n/a | none | Future: file upload to Supabase Storage + a `body_composition` table; treat as point-in-time evidence; never mid-session signal | P4 (future) |
| Blood test upload | n/a | spec only | n/a | none | Future: PDF / CSV upload, parsed manually for key markers; never auto-interpreted | P4 (future) |

States explained:

- **LIVE** = code in mobile + backend reads / writes real data;
  passes through normalised metrics; Coach can reason over it.
- **UI only** = a screen exists but the data model doesn't yet
  capture every needed field.
- **repo-only scaffold** = backend or mobile code exists but no
  user surfaces invoke it yet.
- **spec only** = documented in this audit; no code.

## Next implementation steps in priority order

### P1 (active lane, not yet started)

1. Verify on Build 16 (next iOS / Android paired build): WHOOP
   `last-3-days` UI label flows correctly when today's cycle
   carries only strain (no recovery yet).
2. Verify Android Health Connect read on a non-Galaxy device
   (Pixel Watch or Fitbit-publishing device) — code path is the
   same, but field availability differs per OEM.
3. Confirm BLE CPS / CSC / FTMS Echo Bike fix surfaces "Live data"
   pill on a real bike (commit `a6c7079`).

### P2

1. Grappler Readiness Batch B — extend NextDayCheckin sliders
   (soreness, mood, perceived fatigue).
2. Polar source-attribution differentiation — `direct_polar` vs
   `polar_via_health_connect` rendered distinctly in source breakdown.

### P3+

1. Grappler Readiness Batch C / D, PM5 proprietary protocol, Samsung
   Health Direct, DEXA / blood test uploads.

## Provisional / seed / confidence flags

The mobile `app_athlete_state` shape sent on every `/coach/ask`
already carries:

- `recovery_context.band` + `score_0_100` + `note`
- `load_context.band`
- `fueling_adequacy.band` + `note`
- `readiness_confidence.level` + `reasons_for_low[]`
- `seed_partial` flag when WHOOP fields are missing

Any new source must plug into this shape — never invent a new
top-level "live" path. Missing fields stay `null`; the `_note`
string explains why.

## UI rules summary (already enforced or about to be on next build)

- **iOS** primary card: AppleHealthCard. Health Connect / Samsung
  must NEVER appear as a primary surface on iOS.
- **Android** primary card: SamsungHealthCard (label generic
  "Health Connect" component). Apple Health must NEVER appear as
  a primary surface on Android.
- WHOOP / Polar / Garmin / Oura tucked under the "More sources /
  Add another source" disclosure unless connected.
- WHOOP CSV / Polar export uploads labelled "Imported · historical
  backfill" — never "Live".
- When neither primary is connected: a single "Connect health
  sources" CTA, never duplicated.
- When live BLE bike is connected but the bike doesn't broadcast
  any supported metric stream: explicit honest copy "Connected,
  but no supported metric stream detected. You can still save the
  manual session." — already shipped in commit `a6c7079`.

## What stays MISSING when missing

- **WHOOP RHR / HRV / recovery / strain** — if not connected or
  not yet scored: surface "WHOOP direct metrics are not connected
  or not available yet." Never substitute Apple Health HRV in its
  place.
- **Apple Health HRV** — if user denied permission: surface
  "Apple Health HRV permission denied — re-enable in Settings →
  Lauburu". Never substitute WHOOP HRV.
- **Sleep** — if no source: empty trend; never imputed from steps
  / HR / activity.
- **Steps** — if app was force-killed across the day: missing
  middle hours stay missing; never extrapolated.

## Anti-rules

- Do NOT show a wearable's own "readiness" / "body battery" /
  "recovery" as primary product truth. App-owned Lauburu
  Readiness and Grappler Readiness are product truth; wearables
  are inputs only.
- Do NOT auto-interpret DEXA / blood test uploads. Surface as
  evidence, let the user mark caveats.
- Do NOT import nutrition CSVs without explicit user opt-in per
  file.
- Do NOT block the manual session save path on any source state.
  Manual save must always work.
