# Grappler Readiness — provisional prototype plan

The earliest cautious UI surface for app-owned Grappler Readiness,
designed to be useful right now without overclaiming. Documents
the shape; the implementation lands in a follow-up batch (Batch
B / C / D mapped to NextDayCheckin sliders, TrainingSession
schema, bucket-ring UI per `APP_DEVELOPMENTS.md` standing top-5).

Companion to `HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md`,
`HEALTH_METRIC_APPS_DEVICES_AUDIT.md`, and the existing compute at
`packages/shared/src/backend/services/readiness/grappler-readiness.ts`.

Updated 2026-05-08.

## Grappling Readiness is the core health product

Updated 2026-05-08 against
`CLAUDE-GRAPPLING-READINESS-CORE-REPRIORITISE-01`. **Grappling
Readiness is the core product of the Health tab.** Every other
health surface (per-source cards, source-management settings,
nutrition card, manual log, integrations) is supporting
infrastructure: it exists to feed the readiness compute or to
give the user provenance when a readiness signal is missing /
provisional.

Implication for prioritisation:

- **Critical path** = anything that lets the readiness compute
  return a useful provisional reading from data Aaron's
  testers already have. That's Apple Health (iOS),
  Health Connect (Android), and the Lauburu manual log /
  NextDayCheckin / TrainingSession schemas.
- **Optional enrichment** = WHOOP Direct, Polar AccessLink
  Direct, Bluetooth HR sensor, vendor-export uploads. Each
  improves readiness fidelity but **none is a v1 blocker**.
  Removing them from the critical path means readiness ships
  when hubs are reliable, not when every vendor migration is
  done.
- **Removed from the critical path explicitly:**
  - WHOOP Direct OAuth migration (FS-008) — now optional
    v1.5 enrichment, not a v1 blocker.
  - Polar AccessLink (FS-012) — now optional v2 enrichment.
  - Bluetooth HR sensor (FS-013) — Train-session lane,
    never a readiness path.

Hub-fed wearable data (WHOOP / Polar / Garmin / Concept2 /
ErgZone routed through Apple Health or Health Connect) is an
accepted v1 input — under hub provenance ("WHOOP via Apple
Health", "Polar via Health Connect"), never relabeled as
direct. Vendor exports (CSV / zip) are accepted with truth
label `imported summary`; they enrich the historical context
but are NEVER readiness inputs (`docs/HEALTH_NUTRITION_READINESS_AUDIT.md`
§ 3.1, FS-014 anti-rule).

This positioning supersedes any earlier framing in
`docs/APP_DEVELOPMENTS.md` Priority 2 that treated WHOOP Direct
or Polar AccessLink as health-MVP gates. They aren't.

## Evidence input roadmap (v1 / v2 / v3)

Updated 2026-05-08 against
`CLAUDE-PARALLEL-PRIORITY-SYNC-READINESS-AUTOMATION-01`. The
readiness compute is the core product (see § "Grappling
Readiness is the core health product" above). Direct vendor
integrations (WHOOP, Polar AccessLink) have been removed from
the v1 AND v2 critical paths — they only return as v3
optional enrichment if the readiness compute proves
inaccurate from the inputs below. **Do not let any direct
integration be a shipping gate for readiness.**

### v1 — ships against this set

Already live or shipping in current Codex batches. Aaron's
testers have these on their devices today.

| Input | Source | Status | Notes |
|---|---|---|---|
| Sleep duration | Apple Health / Health Connect `SleepSessionRecord` | live | hub-fed; provenance per § 3.3 of `HEALTH_BACKEND_CONTRACT_FOR_CODEX.md` |
| Resting HR | hub `RestingHeartRateRecord` | live | hub-fed |
| HRV (RMSSD) when present | hub `HeartRateVariabilityRmssdRecord` | live (best-effort) | feeds `autonomic` bucket when source supplies; never synthesised |
| Workouts / training sessions | hub `WorkoutRecord` / `ExerciseSessionRecord` + Lauburu `TrainingSession` | live | feeds `load` bucket |
| Manual training log | Lauburu `TrainingSession` schema | live | direct user input; truth label `live` (manual) |
| Subjective check-in | Lauburu `NextDayCheckin` sliders | partial (Batch B extends) | feeds `subjective` bucket; bucket null when not entered |
| Hub-fed wearable data | WHOOP / Polar / Garmin / Concept2 / ErgZone via Apple Health or Health Connect | live | provenance-labeled "{Vendor} via {Hub}"; NEVER relabeled as direct |

Confidence ceiling for v1 reads: `low` (per § "Confidence
labels in v1"). `medium` reserved for v2+; `high` never returned
by prototype.

### v2 — next ladder, gated on v1 stability

Each v2 input is its own FS-XXX candidate; coders may build
in parallel because the surfaces don't overlap. NONE depends
on FS-008 (WHOOP Direct) or FS-012 (Polar AccessLink).

| Input | FS | What it adds | Source data path | Status |
|---|---|---|---|---|
| Daily journal / Apple-Notes-style check-in | FS-016 | free-text evidence; mood / soreness / context narrative; never a readiness input but informs Why bullets | new mobile UI + per-user storage; redactor extension on any MCP-bound field | planned |
| Blood test uploads | FS-015 | PDF / screenshot / manual headline numbers; quarterly evidence | `manual_imports` table + parser stub; "context only — not medical advice" caption | planned |
| DEXA scan uploads | FS-015 | quarterly body-composition evidence | same upload path as blood test | planned |
| HIIT / conditioning hub-fed | (FS-007 + FS-010 audit aligned) | rower / ergometer / bike sessions written to Apple Health / Health Connect by ErgData / ErgZone / Concept2 logbook / Strava / TrainingPeaks / Intervals.icu | hub `WorkoutRecord` / `ExerciseSessionRecord` provenance | partial (hub path live; needs label hygiene) |
| Body-composition scale (hub-fed) | new — FS-017 | Withings / Garmin Index / Renpho when scale writes to Apple Health / Health Connect | hub `WeightRecord` + `BodyFatRecord` + `LeanBodyMassRecord` | planned |
| Vendor file imports (FIT / TCX / CSV) | FS-014 | training sessions from devices that don't write to a hub | `manual_imports` upload path; truth label `imported summary`; **NEVER readiness input** | planned |
| Subjective slider extensions | (Batch B + C of standing top-5) | soreness / mood / perceived fatigue / drilling-vs-live ratio | extend `NextDayCheckin` + `TrainingSession` schemas | planned |

v2 confidence ceiling per source: `low` for hub-fed and
manual; `medium` only for hub-fed + ≥7 days clean overlap
with manual subjective layer.

### v3 — research-gated; no implementation until proof

These inputs ship ONLY after a proven-device research pass
demonstrates that the data is reliable and that adding it to
the readiness compute meaningfully improves accuracy versus
v1+v2. No coder writes implementation against any v3 input
until that research lands as a doc commit + Aaron approval.

| Input | What it offers | Proof required before any code |
|---|---|---|
| Direct machine data — Rogue Echo Bike | per-second power / cadence / HR during machine-bound sessions | Rogue API exists? Is BLE characteristic exposed? Aaron tester has the device? Does adding the data change readiness output materially vs hub-fed workout summary? |
| Direct machine data — other Rogue equipment (Echo Rower etc.) | same | same; per-device research pass |
| Bluetooth / hub-fed body-composition scales (Withings, Garmin Index, Renpho) — DIRECT path | weight / fat % / muscle / water | only if hub path (v2) demonstrates a gap that direct vendor API would fix; otherwise stay hub-fed |
| Bluetooth spirometry — Airofit | respiratory training metrics; airflow / load / session count | Airofit exposes BLE GATT or vendor SDK? values are clinically reliable for daily readiness signal, not just sales metric? Aaron tester has the device? |
| Bluetooth nasal spirometry / similar respiratory devices | airway dynamics; breath rate variance | same proven-device gate as Airofit |
| Direct WHOOP / Polar (FS-008 / FS-012) | richer recovery / HRV detail | only revisited if v1 + v2 readings prove inaccurate vs Aaron's subjective experience over ≥4 weeks |
| Other improvements to readiness accuracy | TBD | any new input enters at v3 with the same proof gate; no auto-promotion to v1 / v2 |

### Proven-device gate

For any v3 input that requires Aaron to own / test a specific
device, the gate is:

1. Aaron owns or borrows the device for a tester pass.
2. Coder writes a research doc (`docs/RESEARCH_<DEVICE>.md`)
   showing: vendor data path, BLE characteristics if relevant,
   reliability / signal-to-noise observation, comparison to
   the v1 / v2 input it would replace or augment.
3. Agent reviews; Aaron approves the research as worth
   implementation work.
4. Only then does an FS-XXX candidate get written and an
   implementation bundle scoped.

No coder is asked to implement any v3 input as scope for
"just in case". Implementation work follows proof, not
speculation.

### Codex implementation bundles — parallel-runnable

These bundles can run simultaneously without lane collision
(rule 2). Each is a separate `PROMPT-ID` for the next
overnight or paired-up batch. Coders MUST claim only one
bundle per session.

| Bundle | Lane / scope | Files / surfaces | Anti-overlap |
|---|---|---|---|
| **B1: Hub-first v1 prototype card** | mobile UI + service | `apps/mobile/app/(tabs)/health.tsx`, `apps/mobile/src/components/Readiness*`, `apps/mobile/src/services/health-source-ui.ts` | does NOT touch journal / blood / scale storage |
| **B2: Daily journal upload** | mobile UI + per-user storage | new `JournalEntry` schema, journal-only mobile screen, redactor extension | does NOT touch readiness card |
| **B3: Blood test + DEXA upload UI** | mobile UI + `manual_imports` parser stub | upload screen, "context only" caption rendering, PDF / image picker | does NOT touch journal / readiness |
| **B4: NextDayCheckin slider extension (Batch B)** | schema + mobile sliders | `store/training-store.ts` schema; `NextDayCheckinScreen.tsx` | does NOT touch readiness card or upload UIs |
| **B5: TrainingSession schema extension (Batch C)** | schema + session-log UI | `store/training-store.ts` `TrainingSession` shape; session log entry surfaces | does NOT touch B4's slider work; only the session schema |
| **B6: Health-source label hygiene Phase 1** | mobile copy patches | the five files in CODEX-HEALTH-NUTRITION-AUDIT-MOBILE-PHASE-1-LABELS-01 | already in flight via prior commits; do not re-dispatch unless flagged |
| **B7: Hub-fed body-composition scale audit** | docs + mobile read path | `WeightRecord` provenance label rendering | does NOT touch any other bundle |

Three to four of these CAN run in parallel because the file
sets are disjoint. B1 + B2 + B4 are the natural first wave;
B3 + B5 + B7 the second wave. B6 is filler that can land
anywhere because it's copy-only.

### What's explicitly NOT part of v1 / v2

- **WHOOP Direct OAuth migration (FS-008)** — moved to v3
  research-gated. No v1 / v2 work touches this.
- **Polar AccessLink (FS-012)** — moved to v3 research-gated.
- **Bluetooth HR sensor as readiness input (FS-013)** — never;
  Train-session lane only.
- **Direct machine data (Rogue, etc.)** — v3 research-gated.
- **Spirometry (Airofit, nasal)** — v3 research-gated.
- **Body-composition scale via direct vendor API** — only if
  hub path proves insufficient; v3 research-gated.

## Priority — v1 is hub-first

Updated 2026-05-07 against
`CLAUDE-GRAPPLING-READINESS-HUB-FIRST-PRIORITY-01`.
**Grappling Readiness v1 ships against the platform health
hubs (Apple Health on iOS, Health Connect on Android), not
against vendor-direct integrations.** WHOOP Direct, Polar
AccessLink Direct, and Bluetooth HR are explicit
enrichments — they roll into v1.5 / v2, not v1.

Why hub-first:
- Apple Health and Health Connect are already `live` per
  `docs/HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.1 and § 1.2.
  Every Aaron tester device already has them. No vendor
  blocker.
- WHOOP Direct (FS-008) is BLOCKED on Aaron approval +
  Railway → Cloudflare migration. Treating it as a v1 input
  would block Grappling Readiness on a separate workstream.
- Polar AccessLink (FS-012) is `planned` only;
  `docs/POLAR_ACCESSLINK_PLAN.md` is outline-only.
- Hub-routed Polar / WHOOP / Garmin / Concept2 / etc. data
  ALREADY contributes today, just under a different truth
  label (`synced from hub`). v1 honours that data.

### Hub-fed vendor data is hub-fed, not direct

Anti-rule: when WHOOP / Polar / Garmin / Concept2 / ErgZone
data lands via Apple Health or Health Connect, the readiness
compute MUST treat it under the hub source (`apple_health` /
`health_connect`) with the upstream-app provenance label
(e.g. "WHOOP via Apple Health", "Polar via Health Connect").
v1 MUST NOT relabel hub-routed rows as `whoop_direct` or
`polar_direct` even if the user has those vendor accounts.
The truth label captures provenance, not the user's vendor
account state. See `docs/HEALTH_BACKEND_CONTRACT_FOR_CODEX.md`
§ 4 for the three-way Polar matrix; same rule for WHOOP.

### Field-eligibility gate per source

The compute MUST NOT claim HRV / recovery / strain values
unless the source actually supplies those fields. Hub data
varies — Apple Health may not carry HRV unless the upstream
app writes it; some Polar Flow → Health Connect users get HR
samples but not RMSSD. The compute reads what the hub gave
it, hedges everything missing as `provisional`, and never
synthesises a field from another source.

## Minimum v1 inputs

The smallest set of fields v1 reads. Any of these may be
missing on any given day; the compute returns
`confidence: provisional` (or `low`) with the available
subset, never blocks.

| Input | Where it comes from | Required for v1 ship | Notes |
|---|---|---|---|
| Sleep duration | Apple Health `SleepSessionRecord` / Health Connect `SleepSessionRecord` | yes | feed for `sleep` bucket |
| Resting heart rate | Apple Health / Health Connect `RestingHeartRateRecord` | yes | feed for `autonomic` bucket |
| Heart-rate variability (RMSSD) | Apple Health / Health Connect `HeartRateVariabilityRmssdRecord` IF the upstream app wrote it | no — best-effort | feed for `autonomic` bucket when present; bucket falls back to RHR-only when missing |
| Recent training sessions / load | Apple Health `WorkoutRecord` / Health Connect `ExerciseSessionRecord` + Lauburu manual `TrainingSession` | yes (at least one of the two paths) | feed for `load` bucket |
| Subjective soreness / RPE | Lauburu `NextDayCheckin` sliders (Batch B) | best-effort — bucket goes null when not entered | feed for `subjective` bucket |
| Nutrition context | Apple Health / Health Connect `NutritionRecord` OR Lauburu manual nutrition | best-effort — context-only, NEVER a readiness input | rendered as a sidebar / "More sources" disclosure; per `docs/CRONOMETER_IMPORT_FLOW.md` § 6 |

Anti-rule: nutrition is **context only**, never readiness
input. Same for blood test, DEXA, journal — those sources
appear in the UI as evidence but the compute does not read
them.

### Confidence labels in v1

| Label | Meaning | When it returns |
|---|---|---|
| `provisional` | floor; assumes nothing about input veracity | always — every reading carries this floor |
| `low` | enough data to compute, partial provenance | hub data present + at least one Lauburu manual layer |
| `medium` | NOT returned in v1 | reserved for v1.5+ once direct sources clear their seed window per `WHOOP_DIRECT_SETUP.md` § M.3 / `POLAR_ACCESSLINK_PLAN.md` § O.4 |
| `high` | NEVER returned by the prototype | reserved for the post-calibration future state |

Plus the qualifier label "better with connected sources":
when the compute returns `provisional` AND the user has zero
direct sources connected, the UI MUST show a small caption
reading "Better with WHOOP / Polar Direct connected" linking
to the (hidden-by-default) connect surfaces. This is the
single allowed nudge — no other coaching language.

### What stays hidden / disabled in v1

| Surface | State |
|---|---|
| WHOOP Direct connect button | hidden behind veteran "More sources" disclosure; chip says `setup required` per `HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 5.2 |
| WHOOP Direct readiness card | hidden until FS-008 ships AND seed window clears |
| "Polar Direct" / "Polar AccessLink" labels | NEVER appear until POLAR_ACCESSLINK_PLAN ships AND seed window clears |
| Polar AccessLink connect button | hidden until FS-012 ships |
| Bluetooth HR sensor connect | lives in Train tab only; never offered as a readiness input |
| `confidence: medium` chip | not rendered (compute won't return it in v1) |
| `confidence: high` chip | not rendered |
| Per-vendor recovery / strain / HRV claims | gated on source-actually-supplies-the-field per § "Field-eligibility gate"; hidden when the source is silent |

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

## Codex handoff — hub-first v1 prototype

Drop-in for the next mobile batch. Not yet dispatched; bundled
with the existing health-source label audit prompt.

```
PROMPT-ID: CODEX-GRAPPLING-READINESS-V1-HUB-FIRST-01
TYPE: CODEX
LANE: Mobile / Grappling Readiness v1 prototype card

MCP-FIRST: call project.get_current_state.

Reference docs (read these first):
- docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md (this doc) —
  hub-first priority + minimum v1 inputs + confidence labels +
  hidden / disabled surfaces.
- docs/HEALTH_BACKEND_CONTRACT_FOR_CODEX.md § 3 (Health
  Connect per-metric mapping) + § 5 (readiness gating).
- docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md § 4
  (provisional readiness strings) + § 1 (truth labels).

Phase 1 scope (this batch):

1. Implement the Grappler Readiness v1 card in
   apps/mobile/src/components/ — read computeGrapplerReadiness
   output from the existing service, map to band + suggestion +
   why bullets per § "UI shape (target)".
2. Hub-first: read Apple Health (iOS) and Health Connect
   (Android) inputs only. Do NOT add WHOOP-direct or
   Polar-direct read paths. WHOOP / Polar data routed through
   the hub IS in scope and MUST surface with provenance like
   "WHOOP via Apple Health" or "Polar via Health Connect".
3. Confidence labels: render only `provisional` and `low` in
   v1. The `medium` and `high` chips MUST NOT be reachable
   from this UI even if the compute returns them; cap at `low`
   for v1.
4. "Better with connected sources" caption: render when the
   compute returns `provisional` AND zero direct sources are
   connected. One small line, links to the hidden-by-default
   connect surfaces.
5. Missingness: every bucket renders "no data" per
   HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md § 2.3 when its
   input is absent. No fabricated values, no estimates.
6. NO React redesign of unrelated screens. NO Worker route
   addition. NO migration. NO native rebuild. NO version bump.
   NO EAS build.
7. Status report opens with the rule-12 three-field block
   (MCP update attempted / Bridge snapshot run / Stale reason
   if blocked) AND the rule-13 three-section split (automated
   by coder/agent / manual Aaron step / blocked until Aaron
   acts).
8. Status sequence MUST be the four-string ladder per rule 8.

Anti-rules:
- No "you are ready" / "skip training today" language.
- No medical / clinical phrasing.
- No silent passthrough of vendor recovery scores
  (WHOOP recovery, Polar Recovery Pro). v1 only renders
  fields it computed itself.
- No imputation of missing values.
- No HRV / recovery / strain claim unless the source actually
  supplied that field on that day.

Output:
- changed files (mobile prototype card, no other screens)
- four-status compliance per FS-XXX candidate
- recommendation for v1.5 (WHOOP-direct enrichment) once
  v1 lands
- explicit statement: this batch did NOT request, recommend,
  or trigger an EAS build
- rule-12 three-field block + rule-13 three-section split
```

## Anti-rules summary

- No "you are ready" language, full stop.
- No medical / diagnostic claims.
- No silent vendor-score passthrough.
- No imputation of missing values.
- No high-confidence reading until Aaron's subjective calibration
  validates the compute.
- No removal of `provisional` label without explicit owner sign-off
  on a doc commit.
