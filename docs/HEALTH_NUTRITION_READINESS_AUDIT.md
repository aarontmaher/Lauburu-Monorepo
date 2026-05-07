# Health / Nutrition / Readiness — audit spec

The single doc that turns the cross-cutting health-and-nutrition
audit into per-provider status, roadmap rank, beginner-vs-veteran
UX rules, do-not-promote list, and MVP acceptance criteria.

This doc is **spec / backlog only**. No implementation, no
mobile UI, no native rebuild, no version bump, no EAS build.
Code lands in batches downstream gated by the EAS build cost
control rule (`docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build
cost control rule").

Companion to:
- `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` — canonical
  per-provider truth labels + source × metric matrix.
- `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md` — long-form
  per-provider claim audit.
- `docs/HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md` — engineering
  state.
- `docs/WHOOP_DIRECT_SETUP.md`, `docs/WHOOP_POLAR_SYNC_STRATEGY.md`.
- `docs/BLUETOOTH_MVP_SPEC.md`.
- `docs/NUTRITION_TRACKING_PLAN.md`.
- `docs/DEXA_BLOOD_TEST_UPLOAD_PLAN.md`.
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md`.
- `docs/POST_MCP_PRODUCT_LANES.md` (Lane A / Lane B gating).
- `docs/FEEDBACK_SUGGESTIONS.md` (candidate workflow).

Status tags used below:
- `live` — verified on a tester device today.
- `partial` — code path exists; user / owner action or vendor
  setup pending.
- `planned` — doc-only.
- `blocked` — cannot move without an external action (vendor
  approval, Aaron paste, dashboard step).

Updated 2026-05-07.

## 1. Per-provider status

### 1.1 Apple Health (iOS hub)

**Status: live.**

Platform default for iOS. Aggregates from Apple Watch + any
third-party app writing to HealthKit. Un-gated from free tier
(commit `d4827ba`). Missing data stays missing.

Reads today: HR (live + RHR), HRV, sleep duration / stages,
workouts, active calories, dietary nutrition (when written by a
nutrition app like MyFitnessPal / Cronometer).

Lane: A (per `docs/POST_MCP_PRODUCT_LANES.md`). Reliability
holds when Aaron's iPhone surfaces every metric with the
correct truth label and missing fields render as "no data".

### 1.2 Android Health Connect (hub)

**Status: live.**

Platform default for Android. Aggregates from any registered
source app (Fitbit, Samsung Health, Garmin Connect,
WHOOP-via-Health-Connect, Polar Flow, etc.). Un-gated from
free tier.

Reads today: same metric set as Apple Health hub on Android.
Missing data stays missing.

Lane: A. Reliability holds when girlfriend's Android device
surfaces every metric correctly.

### 1.3 Polar via hub

**Status: live.**

Polar Flow → Apple Health (iOS) or Health Connect (Android) →
Lauburu reads from the hub. Data appears under the platform-hub
label, NEVER under "Polar". `friendlyDirectSyncError()` (commit
`a036fd5`) handles the "user is connected but no data today"
case.

Truth label: `synced from hub`. The user-facing card MUST NOT
say "Polar live" or "Polar Direct" when data arrived this way.

### 1.4 WHOOP Direct (OAuth)

**Status: partial — blocked on Railway → Cloudflare migration.**

Code path: `chat-app/src/server/sources/liveWhoopReader.ts` +
Supabase `source_connection_state` row + `WHOOP_DIRECT_SETUP.md`
runbook. The OAuth callback URL is anchored to the deprecated
Railway backend (`docs/WHOOP_DIRECT_SETUP.md` line 14). Until
the callback is migrated to a Cloudflare Worker route AND
WHOOP-side redirect URI is updated AND tokens are stored in
Supabase encrypted columns (not Railway disk), the source
stays `setup required` / `seed/provisional`.

Truth label until migration: `setup required`. Even after
migration, the first 7 days of clean token flow must be
labelled `seed/provisional` before promotion to `live`.

Blocking: Aaron must (a) approve the migration batch, (b) paste
the WHOOP client secret into the Cloudflare Worker via
`wrangler secret put` at migration time, (c) update the WHOOP
developer console redirect URI, (d) verify token flow holds for
≥7 days. None of those four are doable from this repo without
Aaron.

### 1.5 Polar AccessLink / Polar Direct

**Status: planned.**

`Polar Direct` label is **reserved**. Polar's vendor API is
called Polar AccessLink. No code path exists today. MUST NOT
appear in any UI / source label / MCP response until vendor
OAuth wiring + token storage land.

Until the work starts, the only Polar surface is "Polar via
hub" (§ 1.3).

### 1.6 Bluetooth HR sensor (HRS, GATT 0x180D)

**Status: planned.**

Spec'd in `docs/BLUETOOTH_MVP_SPEC.md`. Phase-1 native scaffold
gated on Aaron approval. Train-session data ONLY — never
readiness input. No UI today. The only allowed source label
when wired is `Bluetooth HR sensor`, never "Polar Direct" even
if a Polar HR strap is the device.

### 1.7 Manual check-in / training log

**Status: live.**

`NextDayCheckin` (subjective sliders) + `TrainingSession`
(grappling minutes, drilling vs live) are existing schemas.
Train tab; no backend integration needed. Readiness compute
already accepts these. Truth label: `live` (manual).

### 1.8 Generic conditioning imports — hub-first

**Status: partial (hub path live, file import planned).**

When a third-party conditioning app (ErgData, ErgZone, Rogue,
Concept2 logbook, Strava, TrainingPeaks, Intervals.icu, etc.)
writes to Apple Health or Health Connect, Lauburu reads it via
the hub. The app-side `provenanceLabel` model in
`docs/APP_DEVELOPMENTS.md` Priority 2 documents the contract:

- `sourceApp` — human-readable label from hub provenance.
- `sourceType` — `apple_health` / `health_connect` /
  `fit_file` / `tcx_file` / `csv_file` / `manual`.
- `provenanceLabel` — e.g. "ErgData via Health Connect"; never
  "Concept2 Direct" / "ErgZone Direct" / "Rogue Direct" unless a
  verified direct integration exists.

File import (FIT / TCX / CSV) is `planned`. `manual_imports`
Supabase table can already accept the envelope per
`supabase/migrations/0002_manual_imports.sql`; the parser
routing for FIT / TCX is not yet built.

### 1.9 Nutrition (manual + photo + targets)

**Status: live (manual + photo); targets editable.**

`apps/mobile/src/store/nutrition-store.ts` + `NutritionCard`
+ `health.ios.ts fetchDietaryDailyTotals` + `ai-photo-nutrition.ts`.
Nutrition is **context for trends, never a coaching input** per
`docs/NUTRITION_TRACKING_PLAN.md`. Targets editable; daily
totals + history live.

Truth label: `live` for manual + photo capture; `imported
summary` for Apple Health / Health Connect dietary reads.

### 1.10 Cronometer / nutrition app imports

**Status: planned (hub-first).**

Cronometer writes to Apple Health and Health Connect. The
Lauburu read path picks it up automatically through § 1.1 / 1.2
once Cronometer is connected to the hub on the user's device.
Truth label when surfaced: `synced from hub` with
`provenanceLabel: "Cronometer via Apple Health"` (or
"Cronometer via Health Connect").

Direct Cronometer API integration: NOT planned. Hub path is
the contract.

### 1.11 Blood test uploads

**Status: planned.**

Spec in `docs/DEXA_BLOOD_TEST_UPLOAD_PLAN.md`. User uploads a
blood panel (PDF / screenshot / manual entry of headline
numbers). Captured as **evidence / context for trends**, never
diagnostic / medical surface. No automatic claim language.

Acceptance gate: every rendered blood-test value MUST carry a
"context only — not medical advice" caption. No threshold-based
warnings ("your CRP is high"). Quarterly cadence at most.

### 1.12 DEXA uploads

**Status: planned.**

Same shape as § 1.11 per `docs/DEXA_BLOOD_TEST_UPLOAD_PLAN.md`.
User uploads DEXA scan PDF / manual headline numbers (lean
mass, fat mass, VAT, bone density). Trend context only;
quarterly cadence; no body-composition coaching prompts.

### 1.13 Journal uploads

**Status: planned.**

Free-text journal entries paired with a date stamp. Surfaces in
the Train tab session log as context. Treated as
**evidence/context**, never as fed input to the readiness
compute. Privacy: per-user storage only; never appears in any
MCP / connector response; redactor extension applies if any
journal text ever flows into a control-centre-bound field.

## 2. Provider status summary table

| Provider | Status | Lane | Notes |
|---|---|---|---|
| Apple Health (iOS) | live | A | platform default iOS |
| Health Connect (Android) | live | A | platform default Android |
| Polar via hub | live | A | "synced from hub" — never "Polar live" |
| WHOOP Direct (OAuth) | partial | A | blocked on Railway → CF migration |
| Polar AccessLink | planned | A | "Polar Direct" label reserved |
| BLE HR sensor | planned | C | Train-session only; never readiness |
| Manual check-in / log | live | A | Train tab; readiness input today |
| Generic conditioning (hub) | partial | A | hub path live; file import planned |
| Generic conditioning (FIT/TCX/CSV file) | planned | B | parser routing not built |
| Nutrition (manual + photo + targets) | live | B | context only, never coaching |
| Cronometer / nutrition app | planned | B | hub-first; no direct API |
| Blood test uploads | planned | B | quarterly evidence; no medical advice |
| DEXA uploads | planned | B | quarterly evidence; no body-comp coaching |
| Journal uploads | planned | B | evidence only; never readiness input |
| Garmin / Oura / WHOOP-via-BLE | NOT supported | — | out of scope |

Lane A = `POST_MCP_PRODUCT_LANES.md` Lane A health reliability.
Lane B = post-Lane-A product expansion (sub-priority of #2 in
APP_DEVELOPMENTS.md). Lane C = `BLUETOOTH_MVP_SPEC.md` (separate
Train-session lane).

## 3. P0 / P1 / P2 / P3 roadmap

Each item maps to the FS-XXX candidate workflow in
`docs/FEEDBACK_SUGGESTIONS.md`. Coders MUST NOT promote any
P-rank item past `Implementation-complete, awaiting Agent
functional confirmation` without Aaron's approval line per the
EAS build cost control rule.

### P0 — must hold before anything else expands

| # | Item | Status |
|---|---|---|
| P0.1 | Apple Health hub reliable on Aaron's iPhone (every metric labelled correctly; missing renders as "no data") | live, gated on tester verification |
| P0.2 | Health Connect hub reliable on girlfriend's Android (same as P0.1) | live, gated on tester verification |
| P0.3 | "Polar via hub" label correct everywhere (no "Polar Direct" / "Polar live" leakage) | live in spec; mobile audit pending |

### P1 — health-MVP completion, gated on P0

| # | Item | Status |
|---|---|---|
| P1.1 | WHOOP Direct OAuth callback migrated off Railway → Cloudflare Worker route | partial / blocked on Aaron approval |
| P1.2 | WHOOP token storage migrated to Supabase encrypted columns | planned (paired with P1.1) |
| P1.3 | WHOOP truth label flips from `setup required` to `seed/provisional` after migration; to `live` only after ≥7 days clean | gated on P1.1 + P1.2 |
| P1.4 | Nutrition manual + photo path tester-verified on both devices | live (code); tester verification pending |
| P1.5 | "Polar via hub" label propagation audit — every UI string + MCP response field | mobile audit (Codex Phase-1) |

### P2 — readiness v1, gated on P1

| # | Item | Status |
|---|---|---|
| P2.1 | NextDayCheckin sliders extended (soreness / mood / perceived fatigue) — Batch B | planned |
| P2.2 | TrainingSession schema extended (gi/no-gi, drilling vs live, perceived intensity) — Batch C | planned |
| P2.3 | AthleteStateStrip bucket-ring UI (5 buckets with provenance) — Batch D | planned |
| P2.4 | Grappler Readiness v1 ships with `confidence: provisional` floor; never strong "you are ready" claims; all hedge language | planned |

### P3 — optional expansion, never blocking

| # | Item | Status |
|---|---|---|
| P3.1 | Polar AccessLink (Polar Direct) OAuth wiring | planned |
| P3.2 | Bluetooth HR sensor Phase 1 native scaffold | planned (`BLUETOOTH_MVP_SPEC.md`) |
| P3.3 | Generic conditioning file import (FIT / TCX / CSV) | planned |
| P3.4 | Cronometer hub provenance label rendering polish | planned |
| P3.5 | Blood test upload | planned (`DEXA_BLOOD_TEST_UPLOAD_PLAN.md`) |
| P3.6 | DEXA upload | planned (`DEXA_BLOOD_TEST_UPLOAD_PLAN.md`) |
| P3.7 | Journal upload | planned |

## 4. Beginner vs veteran UX requirements

The same data surface must serve two very different users:

### 4.1 Beginner (default)

A Lauburu tester who has just installed the app and connected
Apple Health / Health Connect for the first time:

- Health tab shows ONE primary card per platform (Apple Health
  on iOS / Health Connect on Android). Other sources hidden
  under a "More sources" disclosure.
- Truth labels rendered prominently next to every metric (no
  bare numbers without source). "live" / "synced from hub" /
  "imported summary" — never numerical without context.
- Nutrition + manual log surfaces are simple targets and
  daily-total bars, not macros breakdowns.
- Readiness UI hidden until Lane B unblocks (per
  `POST_MCP_PRODUCT_LANES.md`); when it ships, beginner sees
  one bucket-ring + one-line "Today's readiness:
  provisional".
- Zero clinical / medical claims. Zero strong "you are ready"
  language.
- Onboarding flow names ONE expected next step at a time
  ("Connect Apple Health" → wait → see metrics → done). No
  multi-source pairing tutorial.

### 4.2 Veteran (Aaron / power user)

The same screens MUST also serve Aaron, who has WHOOP +
Cronometer + multiple data sources + DEXA history:

- "More sources" disclosure expands to per-provider rows with
  the full truth label set + last sync timestamp + missing
  field count.
- Nutrition: macros breakdown + protein-target progress + daily
  total + history view (still no coaching language).
- Readiness UI shows all 5 buckets with per-bucket provenance
  + confidence chip per bucket.
- Blood test / DEXA / journal surfaces appear as quarterly /
  ad-hoc upload entry points; trend graphs render with "context
  only — not medical advice" captions.
- Admin/Dev surface (gated by `isAdminEmail`) shows the
  per-source `connector_health_sources` shape for diagnostic.

### 4.3 Cross-cutting rules

- **No different copy per user-tier today** — Lauburu is not
  multi-tier. The "More sources" disclosure is the only
  veteran-vs-beginner switch in MVP.
- **Same truth labels for everyone.** "live" means the same
  thing on Aaron's screen and on a brand-new tester's.
- **No paid-tier gating for primary sources** (Apple Health,
  Health Connect, manual log, nutrition). Already enforced via
  commit `d4827ba`.

## 5. Do-not-promote-yet list

Floor below every batch in this doc. Mirrors lists in
`docs/BLUETOOTH_MVP_SPEC.md`, `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md`,
`docs/POST_MCP_PRODUCT_LANES.md`, and re-enforced here.

- **No "Polar Direct" / "Polar AccessLink" UI label** until §
  1.5 work ships and is tester-verified.
- **No WHOOP Direct as `live` label** until § 1.4 migration
  ships AND tokens flow ≥7 days clean.
- **No Bluetooth HR sensor as readiness input** ever (Train-
  session data only).
- **No strong readiness claims** ("you are ready", "skip
  training today") on top of unreliable data.
- **No clinical / medical claims** on blood test / DEXA / any
  health metric. Always "context only — not medical advice".
- **No coaching language on nutrition.** Targets + totals only.
- **No Garmin / Oura / WHOOP-via-BLE.** Out of scope.
- **No reading from hub-aggregated data labelled as the
  vendor.** Polar data via Apple Health is "synced from hub",
  never "Polar live".
- **No coder-side `live` label promotion.** Source moves to
  `live` only via Aaron's tester-device approval recorded in
  `FEEDBACK_SUGGESTIONS.md`.
- **No EAS build to verify a health-source phrasing fix.**
  Bundle with the next mobile batch per the EAS build cost
  control rule.

## 6. Acceptance criteria

### 6.1 Health + Nutrition MVP

The MVP is "done" (in the Aaron-tested-on-device sense, NOT the
coder-thinks-it-works sense) when ALL hold:

1. **P0.1 + P0.2 + P0.3 verified.** Apple Health hub on Aaron's
   iPhone + Health Connect hub on girlfriend's Android each
   surface RHR / HRV / sleep / workouts / active calories with
   correct truth labels. "Polar via hub" label propagation
   audited and clean.
2. **Missing data renders as "no data".** No fabricated zeros,
   no implicit fallbacks. Visible across at least one full day
   per source on both devices.
3. **Nutrition card shows daily totals + targets + history**
   with no coaching language. Apple Health "Nutrition" types
   labelled `imported summary` from hub (when present).
4. **WHOOP UI honest**: every WHOOP-related card / chip says
   `setup required` (until P1.1+P1.2 ship) or
   `seed/provisional` (within 7 days post-migration). Never
   `live` until P1.3 unblocks.
5. **No Polar Direct / Polar AccessLink label anywhere.** Even
   in admin-only diagnostic strings.
6. **Friendly error UI** (commit `a036fd5`) ships in tester
   build for WHOOP / Polar disconnect-vs-no-data distinction.
7. **Aaron + girlfriend both confirm in writing** that their
   Health tab is honest and useful for daily training. Recorded
   as `approved_done` against an FS-XXX candidate.

### 6.2 Grappler Readiness v1

Ships only after § 6.1 holds for ≥2 tester-build cycles
without health-source regression. Acceptance:

1. Bucket-ring UI on `AthleteStateStrip` shows all 5 buckets
   (autonomic / sleep / load / grappling / subjective). Each
   bucket renders one of: a number with confidence chip, OR
   "no data" greyed out. Never a fabricated bucket value.
2. Every reading carries `confidence: provisional` floor.
   `confidence: low` / `confidence: medium` allowed once Aaron
   approves; `confidence: high` reserved (never returned by
   the prototype until an explicit doc-commit promotion).
3. Per-bucket provenance line names the source
   (`apple_health` / `health_connect` / `whoop_oauth` /
   `polar_oauth` / `manual` / `missing`).
4. Hedge language only — no "you are ready", no "skip
   training today", no "your readiness is poor". Replace with
   "based on available data, today's bucket suggests…".
5. Aaron has used the prototype across ≥4 training weeks and
   confirmed the readings match his subjective experience
   (recorded as a doc commit). Without that confirmation, the
   UI stays admin-gated.
6. Mobile-side test: open `AthleteStateStrip`, force one
   metric missing, confirm the corresponding bucket renders
   greyed out as "no data" with the literal `provenance:
   missing` chip.
7. No EAS build dispatched solely to verify a readiness
   string. Bundled with at least one other meaningful mobile
   change.

## 7. Codex handoff prompt

Drop-in prompt for the next batch when ready. **Do not run yet.**

```
PROMPT-ID: CODEX-HEALTH-NUTRITION-AUDIT-MOBILE-PHASE-1-LABELS-01
TYPE: CODEX
LANE: Mobile / health source labels + nutrition copy
PRIORITY: Bring mobile UI strings into line with the canonical
truth labels documented in HEALTH_NUTRITION_READINESS_AUDIT.md
+ HEALTH_CONNECTIVITY_TRUTH_SPEC.md.

Phase 1 (this batch): mobile audit + small copy patches ONLY.
NO React UI redesign, NO Worker route addition, NO migration,
NO native rebuild, NO version bump, NO EAS build.

Do:
1. Read docs/HEALTH_NUTRITION_READINESS_AUDIT.md § 1, § 2,
   § 3 (P0 row), § 5 do-not-promote, § 6.1 acceptance criteria.
   Read docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md § 3 truth
   labels.
2. Audit apps/mobile/app/(tabs)/health.tsx (or current Health
   tab entry) and apps/mobile/src/components/IntegrationCards.tsx
   + HealthActionsPanel.tsx + health-source-ui.ts. List every
   user-facing source-label string and map it to one of the
   six canonical labels (live / synced from hub /
   imported summary / seed/provisional / setup required /
   planned). Flag any phrasing that needs to be brought into
   line.
3. Audit apps/mobile/src/services/* + store/* for any "Polar
   Direct", "Polar live", "WHOOP live" (without verification),
   or "Concept2 Direct" / "ErgZone Direct" / "Rogue Direct"
   strings. Flag and propose replacement strings.
4. Confirm the four-status build-readiness wording from
   BACKLOG_AUTOMATION_SYSTEM.md is followed for any
   health-related FS-XXX candidate in FEEDBACK_SUGGESTIONS.md.
5. NO React UI implementation in this batch. Audit + small
   copy patches (≤20 lines / file) only.
6. Bundle any small phrasing fix with the next mobile batch
   (do NOT spin a build for a copy fix per the EAS build cost
   control rule).
7. apps/mobile tsc --noEmit clean if any patches land.
8. Status report MUST use the four-string sequence
   (Implementation-complete, awaiting Agent functional
   confirmation → Agent-confirmed → Aaron-approved → Built/
   tester-ready) per BACKLOG_AUTOMATION_SYSTEM.md. Never
   "fully complete".

Output:
- changed files (docs + small mobile copy patches)
- list of mismatched source labels found per file
- list of "Polar Direct" / vendor-direct violations
- four-status compliance per FS-XXX candidate
- recommendation for Phase 2 (connector_health_sources
  Supabase migration + Worker integrations.get_health_sources
  tool)
- committed yes/no + SHA if yes
- explicit statement: this batch did NOT request, recommend,
  or trigger an EAS build
```

## 8. Anti-rules

- **Spec-only here. No code.** Implementation lives in the
  per-provider docs (`WHOOP_DIRECT_SETUP.md`,
  `BLUETOOTH_MVP_SPEC.md`, etc) and in coder batches; this
  doc only ranks and gates.
- **No coding to "fully complete".** Status reports MUST use
  the four-string build-readiness wording from
  `BACKLOG_AUTOMATION_SYSTEM.md`.
- **No EAS build dispatched solely to verify a phrasing or
  source-label fix.** Bundle with the next meaningful mobile
  batch.
- **No reading-from / writing-to MCP responses without truth
  labels.** Every metric-source mention in any
  `/mcp/v2` / `/api/control_centre` response carries one of
  the six canonical labels.
- **No clinical or coaching language anywhere in this surface.**
  Nutrition is context. Blood test is context. DEXA is
  context. Readiness is provisional with hedge language.
- **No coder-side promotion** of any "planned" item to
  "live" without Aaron's tester-device approval line in
  `FEEDBACK_SUGGESTIONS.md`.
- **No deletion of existing technique / website-project
  suggestions** — those live in the website MCP and are
  product backlog, not current-dev state.
- **No mobile UI changes from this commit.**

## 9. Cross-references

- `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` — canonical truth
  labels + source × metric matrix. THIS doc adds rank, UX
  tiers, acceptance.
- `docs/POST_MCP_PRODUCT_LANES.md` Lane A / Lane B —
  reliability before readiness UI.
- `docs/BLUETOOTH_MVP_SPEC.md` — BLE Train-session lane.
- `docs/NUTRITION_TRACKING_PLAN.md` — nutrition contract.
- `docs/DEXA_BLOOD_TEST_UPLOAD_PLAN.md` — quarterly uploads.
- `docs/WHOOP_DIRECT_SETUP.md` — WHOOP runbook.
- `docs/WHOOP_POLAR_SYNC_STRATEGY.md` — anti-rules.
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` — readiness
  compute spec.
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build cost
  control rule" — applies to every batch derived from this
  doc.
- `docs/FEEDBACK_SUGGESTIONS.md` — candidate intake +
  approval workflow for every P-rank item above.
