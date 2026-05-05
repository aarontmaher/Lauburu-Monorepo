# Grappler Readiness — provisional prototype plan

The earliest cautious UI surface for app-owned Grappler Readiness,
designed to be useful right now without overclaiming. Documents
the shape; the implementation lands in a follow-up batch (Batch
B / C / D mapped to NextDayCheckin sliders, TrainingSession
schema, bucket-ring UI per `APP_DEVELOPMENTS.md` standing top-5).

Companion to `HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md`,
`HEALTH_METRIC_APPS_DEVICES_AUDIT.md`, and the existing compute at
`packages/shared/src/backend/services/readiness/grappler-readiness.ts`.

Updated 2026-05-06.

## Principles

1. **App-owned, not vendor-mirrored.** Lauburu's Grappler
   Readiness is computed on-device-side from normalised
   metrics — never a passthrough of WHOOP recovery, Garmin Body
   Battery, or Oura readiness. External sources are evidence,
   not answers.
2. **Provisional by default.** Until Aaron verifies the prototype
   matches his subjective readiness across at least a few
   training weeks, every reading is labelled `provisional`.
   Confidence stays low/medium even when data is rich.
3. **Missingness wins over confidence.** When required signals
   are absent, the UI says so plainly — does not impute,
   substitute, or extrapolate.
4. **No medical claims.** No "ready to compete", no "you have
   adrenal fatigue", no "your nervous system is depleted". The
   UI uses cautious language: "moderate", "consider lighter
   intensity", "rest is reasonable today".
5. **Manual-only path is honest.** When no health source is
   connected, the prototype renders from manual check-ins +
   training logs alone — and labels that fact.

## UI shape (target)

Surfaces on the Home tab below `AthleteStateStrip`. Owner-
gateable so it can ship to a small cohort first if helpful.

```
┌────────────────────────────────────────────┐
│  Grappler Readiness — provisional          │
│  Confidence: low                           │
│                                            │
│  Today's suggestion:                       │
│  Moderate session — consider technique     │
│  + light positional sparring; avoid        │
│  high-intensity rolling.                   │
│                                            │
│  Why                                       │
│  • Sleep flag (manual): 5h reported        │
│  • HRV trend: not connected                │
│  • Last hard session: yesterday            │
│                                            │
│  Missing                                   │
│  • Apple Health HRV — connect for richer   │
│    readiness                               │
│  • WHOOP recovery score — secondary input  │
│                                            │
│  Sources used                              │
│  • Manual check-in (this morning)          │
│  • Training logs (last 7 days)             │
└────────────────────────────────────────────┘
```

Three layout cases:

### Case 1 — manual-only (no Apple Health / Health Connect)

- Confidence: **low**.
- Suggestion: cautious. Default to "moderate" unless soreness ≥ 4
  or sleep < 4h, in which case "rest / light recovery".
- Why bullets: pull from NextDayCheckin slider readings only.
- Missing: lists Apple Health (iOS) / Health Connect (Android)
  with one-tap "Connect" CTA.
- Sources used: `manual_checkin`, `manual_training_log`.

### Case 2 — primary connected (Apple Health on iOS or Health Connect on Android)

- Confidence: **medium** (when 7+ days of data exist) or **low**
  (less).
- Suggestion: blends manual signal with HRV/RHR/sleep_hours
  z-scores from the `Lauburu Readiness` compute already in
  `packages/shared/src/backend/services/readiness/lauburu-readiness.ts`.
- Why bullets: top 3 contributing signals from the readiness
  compute, with provenance ("Apple Health HRV: 38ms vs 42ms
  baseline").
- Missing: WHOOP recovery (richer cross-check), grappling-load
  fields (Batch C dependency).
- Sources used: `apple_health` or `health_connect`, plus the
  manual layers.

### Case 3 — primary + WHOOP/Polar connected

- Confidence: **medium** to **high** depending on data depth.
- Suggestion: same logic, with WHOOP recovery as a cross-check.
  When WHOOP and Apple/HC disagree (e.g. WHOOP says 35,
  app-computed says band=high) — surface BOTH, label them, do
  not silently average.
- Why bullets: include the cross-check sentence ("WHOOP recovery:
  35 (low) — vs app-computed band: moderate").
- Missing: grappling-load fields (Batch C dependency).
- Sources used: full list including `whoop_direct` /
  `polar_direct` / `polar_via_health_connect`.

## Computation (already implemented, follow-up wiring)

`packages/shared/src/backend/services/readiness/grappler-readiness.ts`
already exports `computeGrapplerReadiness(input)` returning
five buckets: `autonomic`, `sleep`, `load`, `grappling`,
`subjective`. Today three buckets work (autonomic, sleep, load);
two return null pending Batches B (NextDayCheckin sliders) and
C (TrainingSession schema).

Prototype reads the existing compute output directly:

- Map `score_0_100` to a band (low / moderate / high).
- When two of the five buckets are null, force `confidence:
  'low'` and label "provisional".
- When ≤1 bucket is null AND 7+ days of data exist, allow
  `confidence: 'medium'`.
- `confidence: 'high'` is reserved for the future state where
  all five buckets are live AND the compute has been calibrated
  against Aaron's subjective readiness for ≥4 weeks.

## What the prototype does NOT do

- Does NOT show a single number alone. The UI always pairs the
  band with the suggestion + the why bullets. A bare "73/100"
  is misleading without context.
- Does NOT auto-prescribe specific training (no "do 3x5min
  rounds at 75% intensity"). Suggestions are coarse and
  cautious.
- Does NOT claim recovery from injury. Injury notes from manual
  check-in are surfaced as evidence ("user reported left knee
  pain"), never interpreted.
- Does NOT recommend supplements, drugs, or medical action.
- Does NOT replace Lauburu Readiness card. They sit
  side-by-side; Lauburu Readiness is the objective layer,
  Grappler Readiness adds the grappling-specific subjective +
  load layers.

## Wiring sequence (small batches, each safe)

This document is the contract; implementation is gated:

1. **Batch B** (next safe batch after device-confirmation of
   v15/Build 16): extend `NextDayCheckin` slice in
   `store/training-store.ts` with sliders for soreness, mood,
   perceived fatigue. Pure schema + UI.
2. **Batch C**: extend `TrainingSession` schema with
   `gi/no-gi`, `drilling_minutes`, `live_minutes`,
   `perceived_intensity`. The grappling bucket compute starts
   returning non-null.
3. **Batch D**: bucket-ring UI on `AthleteStateStrip` — five
   small ring meters, one per bucket, with provenance on tap.
4. **Prototype card on Home** (this doc): renders the band +
   suggestion + why + missing + sources_used. Provisional label
   stays for at least the first month of real-data testing.
5. **Calibration window**: Aaron uses the prototype for ≥4
   weeks, comparing the band each morning to his subjective
   read. Adjust weights in `computeGrapplerReadiness()` based
   on the disagreement pattern.
6. **Confidence promotion**: only after calibration, the prototype
   can return `confidence: 'high'` for days where all five
   buckets are live.

Each batch is its own safe lane per `BACKLOG_AUTOMATION_SYSTEM.md`
Lane 2 (build autopilot with confirmation).

## Anti-rules summary

- No "you are ready" language, full stop.
- No medical / diagnostic claims.
- No silent vendor-score passthrough.
- No imputation of missing values.
- No high-confidence reading until Aaron's subjective calibration
  validates the compute.
- No removal of `provisional` label without explicit owner sign-off
  on a doc commit.
