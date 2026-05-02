# Privacy Policy — Lauburu Grappling Map

_Last updated: 2026-05-01_

Lauburu Grappling Map ("the app") is a personal grappling tracker and
training assistant. This policy describes what data the app collects,
how it is used, where it is stored, and your control over it.

## 1. Health and fitness data

The app reads (with your explicit permission) health and fitness data
from the following platforms and services:

- **Apple Health (HealthKit)** — sleep, steps, heart rate, heart rate
  variability (HRV), resting heart rate, active energy burned, workouts,
  and walking/running distance.
- **Android Health Connect** — heart rate, heart rate variability,
  resting heart rate, sleep, steps, exercise sessions, active calories
  burned, and historical health data (`READ_HEALTH_DATA_HISTORY`).
- **WHOOP CSV imports** — recoveries, sleeps, cycles, and workouts that
  you export from your WHOOP account and import into the app.
- **WHOOP Direct (OAuth, where enabled)** — recovery, sleep, cycle,
  strain, and workouts authorised through WHOOP's API.
- **Polar Flow / Samsung Health (via Health Connect, where applicable)**
  — the same metric categories listed above, surfaced through Health
  Connect.
- **Cronometer (where you connect it)** — calories, protein, carbs, fat.

All metric reads are initiated by you. You can revoke any platform
permission at any time from Apple Health, Android Health Connect, or the
respective service's own settings; the app stops reading those metrics
immediately.

`READ_HEALTH_DATA_HISTORY` is requested specifically so the app can
build personal trend baselines (7-day, 14-day, 30-day, 90-day rolling
averages, variability, and consistency) on first sync, after a device
reset, or when you connect a new tracker. Backfills are explicitly
initiated by you.

## 2. Bluetooth / BLE and location permissions

The app uses Bluetooth Low Energy (BLE) to pair with:

- FTMS-compatible cardio machines (bikes, rowers, ski-ergs).
- Concept2 PM5 monitors.
- Bluetooth heart-rate straps (Polar H10, H9, Verity Sense; Wahoo
  TICKR; Scosche Rhythm+; Garmin straps).
- Echelon-branded equipment via name-based identification.

`BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `ACCESS_FINE_LOCATION`, and
`ACCESS_COARSE_LOCATION` are used solely to discover and pair with
these devices. On Android API levels below 31, the BLE stack
requires `ACCESS_FINE_LOCATION` to scan; the app does **not** derive,
store, or transmit your physical location.

## 3. Storage and processing

- **Primary storage — Railway-hosted backend.** Your normalised daily
  metrics, training sessions, AI Coach context, and feedback
  submissions are stored in a Postgres database on Railway, isolated
  per-account. Data is encrypted in transit (HTTPS / TLS) and at rest
  (Railway-managed encryption).
- **Secondary mirror — Supabase.** Selected aggregate-only data is
  mirrored to a Supabase project for redundancy and read-side
  performance. Row-level security ensures each user can only access
  their own records.
- **On-device caching.** The mobile app caches your most recent metrics,
  training history, and preferences using OS-secure storage
  (Keychain / Keystore via expo-secure-store) so the app is responsive
  offline. Clearing the app or signing out removes this cache.

## 4. AI Coach and analysis

When you ask the AI Coach a question, the app sends a structured
request containing:

- the question you typed,
- your current Lauburu Readiness summary,
- your normalised daily metrics for the last up to 90 days, and
- relevant training-context fields (workout summaries, nutrition
  summaries, source-health flags).

The AI Coach reasons over your data only — it does not blend data from
other users. Aggregate or population-level insights are not enabled by
default.

## 5. What we do NOT do

- We do **not** sell your data.
- We do **not** use your data for advertising or for personalised ads.
- We do **not** share identifiable health data with third parties for
  marketing.
- We do **not** track your physical location.

## 6. User controls

- **Revoke platform access** — disable any source from Apple Health,
  Android Health Connect, WHOOP, Cronometer, or Polar settings.
- **Disconnect inside the app** — the Settings screen lists every
  connected source with a Disconnect action that removes the active
  authorisation.
- **Delete your account** — email
  [aaron.t.maher@gmail.com](mailto:aaron.t.maher@gmail.com) and we will
  remove your account and the associated stored data within 30 days.
- **Export** — on request we will provide a copy of your stored data
  (normalised metrics, training sessions, AI Coach context).

## 7. Security

- HTTPS / TLS for all network requests.
- OS-secure storage for tokens and session credentials on-device.
- Server-side row-level security on Supabase mirror.
- Service-role secrets used only for backend-to-database operations,
  never exposed to the client.

## 8. Tester / internal-testing builds

Internal testing builds (Google Play Internal Testing, TestFlight) are
restricted to invited testers only. Bug-report and feedback content
submitted from inside the app may include device model, OS version,
app build number, and a free-text description; these submissions are
stored on the same Railway backend and are visible only to the
project owner.

## 9. Contact

For privacy questions, deletion requests, or to export your data,
email **aaron.t.maher@gmail.com**. We reply within 30 days.

## 10. Changes

If this policy changes materially we will post the updated text at the
canonical URL and bump the "Last updated" date above. Continued use of
the app after the update constitutes acceptance.
