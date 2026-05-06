# Grappler Readiness — build plan (Batches A–D)

Concrete batch sequence for building Grappler Readiness from
"docs only" → "available now without overclaiming" → "fully
calibrated app-owned readiness". Companion to
`GRAPPLER_READINESS_PROTOTYPE_PLAN.md` (the UI shape) and the
existing compute at
`packages/shared/src/backend/services/readiness/grappler-readiness.ts`.

Updated 2026-05-06.

## Principle

Readiness is **app-owned, missingness-aware, provisional by
default.** External wearable scores are evidence inputs, never
passthrough. Each batch ships only what is honest given the
current data shape; nothing claims more confidence than the data
supports.

## Architecture gates before user-facing UI

Do not ship another user-facing readiness surface until these gates
are true in a tester build:

- Source hierarchy is explicit: manual check-ins and training logs are
  the baseline; Apple Health on iOS and Health Connect on Android are
  primary verified health sources; WHOOP/Polar direct or export data
  are optional advanced evidence; CSV exports are historical backfill.
- Missing health data stays missing. No bucket may substitute a vendor
  score, inferred HRV, or generic activity shape when the real metric
  is absent.
- Confidence is separate from score. Manual-only can produce a
  provisional low-confidence state, but cannot present as calibrated.
- Readiness score display is gated behind verified source-state copy,
  audit metadata, and explicit "provisional" labelling.
- Apple Health verification is iOS-only. Health Connect verification is
  Android-only. Cross-platform copy must use the platform source name.
- WHOOP/Polar data can enrich provenance and confidence, but cannot
  replace the app-owned readiness calculation.
- Export/CSV historical backfill can improve baselines, but must be
  labelled as historical evidence rather than live readiness.

## Batch A — Available now (no readiness engine work)

Status: ready to ship in v16 / Build 17 alongside the other
repo-only work.

What lands in Batch A:

- Apple Health (iOS) / Health Connect (Android) source status —
  already on `main` (commit `d4827ba`, ships in v15 / Build 16).
- Manual check-ins via existing NextDayCheckin slice — already
  live, fields covered by the existing schema.
- Training logs via existing `training-store.ts` — already live.
- Provisional readiness card on Home — DOC-ONLY tonight; UI
  shell ships in Batch A.5 once primary cards are confirmed
  working on real devices.
- Strict labelling rules: "provisional", "Confidence: low",
  "Based on manual check-in only" / "Health data not connected
  yet". No HRV claims unless direct HRV data is present.

Out of Batch A:

- Subjective sliders beyond what NextDayCheckin already has.
- Grappling-specific fields (gi/no-gi, drilling vs live).
- Bucket-ring UI on AthleteStateStrip.

Verification:

- Aaron + girlfriend confirm v15 / Build 16 primary health cards
  surface and connect.
- Provisional readiness card renders on Home with low confidence
  in the manual-only case (most users will start here).

## Batch B — Next-day check-in sliders

Owner: extends `NextDayCheckin` slice in
`apps/mobile/src/store/training-store.ts`. UI is one collapsed
form per day on the Check-in tab.

Sliders to add (or extend if any partial fields exist):

- **Energy** — 1–10
- **Soreness** — 1–10
- **Sleep quality** — 1–10
- **Motivation** — 1–10
- **Pain / injury** — boolean + free-text note
- **How training felt** — 1–10
- (existing) Mood, stress

Rules:

- Sliders are optional — user can submit a check-in with any
  subset filled in.
- The `subjective` bucket in `computeGrapplerReadiness()` starts
  returning non-null when ≥3 sliders are filled in the last
  24h.
- The `pain / injury` field, when set, surfaces in the readiness
  "Why" bullets verbatim (no interpretation: just "user reported
  left knee pain").
- Comparison: each slider's value can be displayed alongside the
  prior day's reading so the user sees their own trend.

Verification:

- Save a check-in with all sliders filled — `useTrainingStore`
  state shows the new fields.
- `computeGrapplerReadiness` returns non-null for `subjective`
  bucket on a day with ≥3 sliders.
- Readiness card "Why" bullets pull from the most-recent
  check-in.

Risk level: medium. Schema change in `training-store.ts` plus a
form UI. Lane 2 per `BACKLOG_AUTOMATION_SYSTEM.md`.

## Batch C — Grappling-specific training log fields

Owner: extends `TrainingSession` schema in
`apps/mobile/src/store/training-store.ts`. UI on Train tab when
session type is `grappling`.

Fields to add:

- **gi / no-gi** — enum.
- **drilling minutes** — number.
- **live minutes** — number (rolling, positional, situational).
- **perceived intensity** — 1–10.
- **training partner names / belts** (optional, free text) —
  context only, never analysed.

Rules:

- The `grappling` bucket in `computeGrapplerReadiness()` starts
  returning non-null when at least one grappling session has
  been logged in the last 7 days with `live_minutes` filled in.
- Acute / chronic ratio computation can include grappling
  sessions weighted by perceived intensity × live minutes.
- Old training logs without these fields stay valid — the
  schema is additive.

Verification:

- Log a grappling session with new fields → the `grappling`
  bucket in readiness output is non-null.
- Old sessions still load without crash (additive schema).

Risk level: medium. Lane 2.

## Batch D — Bucket-ring UI + advanced visualisation

Owner: `AthleteStateStrip.tsx` extended with five small ring
meters (autonomic / sleep / load / grappling / subjective). On
tap, each ring expands to show provenance (which signals
contributed, which were missing).

Rules:

- Rings show the bucket's `score_0_100` as a circular fill.
- Missing buckets render as a hollow ring with a "—" centre,
  not a 0 (zero would imply a measured low score).
- Provenance modal lists the contributing signals in plain
  language ("HRV from Apple Health: 38ms vs 42ms baseline" /
  "WHOOP recovery: not connected").
- Tap-and-hold on the ring → "Why this score?" disclosure.

Verification:

- All five rings render with correct fill / hollow state.
- Tap expands to provenance list.
- Missing buckets stay hollow; not zero.

Risk level: medium. Lane 2.

## Batch E — Calibration window (Aaron-driven, not code)

After Batches A–D, the prototype runs for ≥4 weeks. Each
morning Aaron compares the Grappler Readiness band to his
subjective read and notes the disagreement pattern.

Output: a `docs/GRAPPLER_READINESS_CALIBRATION_NOTES.md` file
(future) tracking the drift. After 4 weeks of consistent
alignment, the prototype graduates from `provisional` to
calibrated; weight tuning in
`computeGrapplerReadiness()` is an explicit doc-committed
change, not a silent refit.

Rules:

- No silent weight changes.
- No removal of `provisional` label without a doc commit.
- Confidence promotion to `high` is reserved for Aaron's
  explicit sign-off after the calibration window.

## Batch F — More-data integrations (parallel to Batches A–E)

Doesn't gate Batches A–E. Lands as parallel side-batches when
each dependency is ready:

- WHOOP / Polar export backfill — UI labelled `historical_upload`
  per `WHOOP_POLAR_SYNC_STRATEGY.md`. Adds richer evidence to
  the autonomic + sleep buckets.
- WHOOP / Polar direct sync — adds live cross-check vs
  Apple Health / Health Connect. Recovery score surfaces
  alongside the app-owned readiness, never replacing it.
- HIIT / conditioning capture — feeds the `load` bucket via
  per-set strain estimates.
- Nutrition trend context — out of readiness directly per
  `NUTRITION_TRACKING_PLAN.md` "What nutrition NEVER does"
  rule 1.
- DEXA / blood — out of readiness directly per
  `DEXA_BLOOD_TEST_UPLOAD_PLAN.md`.

## Batch G — Advanced (gated)

Only after Batches A–F are stable AND the AI provider lane
unblocks per `AI_PROVIDER_STRATEGY.md`:

- Grappler Readiness model refinement based on calibration
  window data.
- Multi-window trend visualisation on the Home tab.
- Athlete memory candidates auto-surfaced for owner promotion.
- Paid AI summarisation of the Why bullets.
- Aggregate cohort readiness benchmarks (k-anonymity gated;
  consent gated).

This batch is intentionally vague — it lands when the
foundation is stable and the gating triggers in
`AI_PROVIDER_STRATEGY.md` + `AI_MONETISATION_AND_USAGE_STRATEGY.md`
all clear.

## Anti-rules across all batches

- Do NOT copy WHOOP / Garmin / Oura readiness directly. App-
  owned compute is the truth; vendor scores are evidence.
- Do NOT make HRV / RHR / fatigue claims unless direct data is
  present.
- Do NOT promise daily readiness in environments where Apple
  Health / Health Connect aren't connected — manual-only path
  is honest about its limits.
- Do NOT remove the `provisional` label without an explicit
  doc-committed calibration record.
- Do NOT auto-prescribe specific training (no "do 3x5min rounds
  at 75%"). Suggestions stay coarse and cautious.
- Do NOT make medical / diagnostic claims, ever.
- Do NOT include readiness band in any paid AI prompt unless
  the user has opted that feature in.
