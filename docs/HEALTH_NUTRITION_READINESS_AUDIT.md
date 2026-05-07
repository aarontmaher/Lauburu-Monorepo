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

### 1.4 WHOOP — Direct, API, export, seed

WHOOP has four distinct flavours in this codebase. Each has
its own status / truth label / unblock path. Coders MUST NOT
collapse them into a single "WHOOP" surface in any UI / MCP
response / connector text — they answer different questions.

#### 1.4.a WHOOP Direct (OAuth via Cloudflare Worker)

**Status: partial — blocked on Railway → Cloudflare migration.**

Code path: `chat-app/src/server/sources/liveWhoopReader.ts` +
Supabase `source_connection_state` row + `WHOOP_DIRECT_SETUP.md`
runbook. The OAuth callback URL is anchored to the deprecated
Railway backend (`docs/WHOOP_DIRECT_SETUP.md` line 14). Until
the callback is migrated to a Cloudflare Worker route AND
WHOOP-side redirect URI is updated AND tokens are stored in
Supabase encrypted columns (not Railway disk), this flavour
stays `setup required` / `seed/provisional`.

Truth label until migration: `setup required`.

Blocking: Aaron must (a) approve the migration batch, (b) paste
the WHOOP client secret into the Cloudflare Worker via
`wrangler secret put` at migration time, (c) update the WHOOP
developer console redirect URI, (d) verify token flow holds for
≥7 days. None of those four are doable from this repo without
Aaron.

#### 1.4.b WHOOP API (vendor-native pull)

**Status: partial — same code path as 1.4.a; same blockers.**

WHOOP exposes a developer API (recovery / strain / sleep /
workouts / cycles) reached via the same OAuth tokens 1.4.a
manages. Once 1.4.a is unblocked, the API surface is the
single read path. There is **no separate API key model** —
auth is the OAuth token. Coders MUST NOT introduce a "WHOOP
API key" config field; the OAuth token IS the API credential.

Truth label tracks 1.4.a: stays `setup required` until the
callback migration ships; flips to `seed/provisional` for the
first 7 days post-migration; only then `live`.

#### 1.4.c WHOOP raw export (CSV / zip upload)

**Status: app-side ready.**

User exports their WHOOP data from the WHOOP app (Account →
Export Data) and uploads the resulting CSV / zip to the manual
imports surface. `manual_imports` Supabase table accepts the
shape per `supabase/migrations/0002_manual_imports.sql`;
parser version flagged on each row.

Truth label when surfaced: `imported summary`. The data is
aggregate (daily / weekly), not real-time. Per-event timing
beyond what WHOOP includes in the export is NOT preserved.

Independence from 1.4.a / 1.4.b: this flavour does **not**
require WHOOP OAuth or vendor API connectivity. It works
when WHOOP API access is broken, paused, or never set up.
Useful as a fallback during the Railway → Cloudflare migration
and as a first-day onboarding option for new users.

Anti-rule: WHOOP export rows MUST NOT be cross-labelled as
`live` even when imported on the same day. The truth label
captures provenance, not freshness.

#### 1.4.d WHOOP seed / provisional window

**Status: defined here; enforced by 1.4.a + 1.4.b.**

The 7-day post-migration window during which any new WHOOP
direct connection produces readings labelled
`seed/provisional`, regardless of how much data has flowed.
The window protects against over-claiming during initial sync,
auth retry storms, and timezone-boundary edge cases. Promotion
to `live` requires:

1. ≥7 calendar days of clean token flow (no auth drops, no
   rate-limit errors, no shape mismatches).
2. At least one daily reading per day of that window for
   recovery + sleep + strain.
3. Aaron's tester-device confirmation that the readings match
   his subjective experience.
4. An explicit `approved_done` line in
   `docs/FEEDBACK_SUGGESTIONS.md` against FS-008.

Until all four hold, the truth label stays `seed/provisional`
and Grappler Readiness MUST treat WHOOP-derived inputs as
`confidence: low` at most. No `confidence: high` from
WHOOP-direct data, ever.

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

### 3.1 Per-source decision matrix

For every source in § 1, the six fields the implementation
team needs at a glance: current state / blocker / next step /
what beginners must NOT see / what veterans MAY see /
readiness-compute eligibility now / readiness-compute
eligibility later. Sources stay listed in § 1 order.

| § | Source | Current | Blocker | Next step | Beginner hides | Veteran sees | Readiness now | Readiness later |
|---|---|---|---|---|---|---|---|---|
| 1.1 | Apple Health (iOS hub) | live | — | tester verify on Aaron's iPhone (P0.1) | nothing | full per-metric truth labels | direct input under "synced from hub" | direct input |
| 1.2 | Health Connect (Android hub) | live | — | tester verify on girlfriend's Android (P0.2) | nothing | full per-metric truth labels | direct input | direct input |
| 1.3 | Polar via hub | live | — | label-propagation audit (P1.5) — never "Polar Direct" leakage | "Polar Direct" / "Polar live" labels | "Polar via Apple Health" provenance line | upstream of Apple Health / Health Connect; counted as hub | hub |
| 1.4.a | WHOOP Direct (OAuth via CF Worker) | partial | Railway → CF Worker migration (FS-008) | Aaron approves FS-008 → migrate callback | the entire WHOOP card until P1.1 ships | "setup required" chip with one-click connect button | NOT eligible | eligible at `confidence: low` once 1.4.d clears |
| 1.4.b | WHOOP API (vendor-native pull) | partial | tracks 1.4.a | flips on with 1.4.a | as 1.4.a | recovery / strain / sleep panels with `seed/provisional` chips for first 7 days | NOT eligible | eligible at `confidence: low` once 1.4.d clears |
| 1.4.c | WHOOP raw export (CSV / zip) | app-side ready | — | tester-verify upload flow on iOS + Android | the upload card itself (advanced surface) | `manual_imports` upload button + provenance "imported summary" | NOT eligible (truth label `imported summary`) | NEVER eligible — provenance ≠ freshness |
| 1.4.d | WHOOP seed / provisional window | defined | depends on 1.4.a/b | enforce in compute (Lane B, P2.4) | nothing — chip is visible to all | same chip, with explicit countdown to `live` | NOT eligible | eligible at `confidence: low` only |
| 1.5 | Polar AccessLink | planned | AccessLink credentials + OAuth wiring | scope after FS-008 lands | the entire surface | nothing yet | NOT eligible | hub-equivalent input once shipped |
| 1.6 | BLE HR sensor (HRS GATT 0x180D) | planned | native scaffold (Aaron approval gate) | follow `BLUETOOTH_MVP_SPEC.md` Phase 1 | the entire surface | scan-and-pair admin card | NEVER eligible — Train-session only | NEVER eligible |
| 1.7 | Manual check-in / training log | live | — | Batch B/C extensions (P2.1/P2.2) | nothing | sliders + history | direct input (subjective bucket) | direct input |
| 1.8 | Generic conditioning — hub | partial (hub live, file import planned) | FIT / TCX / CSV parser routing | scope file-import after P0/P1 | "Concept2 Direct" / "ErgZone Direct" / "Rogue Direct" labels | provenance label "ErgData via Health Connect" etc. | hub-routed (load bucket) | hub-routed |
| 1.9 | Nutrition (manual + photo + targets) | live | — | tester verify P1.4 | macros breakdown / coaching language | macros breakdown + protein-target progress | NOT eligible (context only) | NEVER eligible — context only |
| 1.10 | Cronometer / nutrition app | planned | hub onboarding flow + provenance label rendering polish | document hub-first contract | "Cronometer Direct" label | "Cronometer via Apple Health" provenance line | NOT eligible | NEVER eligible — hub feeds nutrition; nutrition is context |
| 1.11 | Blood test uploads | planned | upload UI + redactor extension + threshold language audit | scope after P2 | the entire surface | quarterly upload entry + trend graph + "context only — not medical advice" caption | NEVER eligible | NEVER eligible — context only |
| 1.12 | DEXA uploads | planned | as 1.11 | scope after P2 | the entire surface | quarterly upload entry | NEVER eligible | NEVER eligible — context only |
| 1.13 | Journal uploads | planned | per-user storage + redactor extension on any MCP-bound field | scope after P2 | nothing — visible but optional | journal entries paired with session log | NEVER eligible | NEVER eligible — evidence only |

Anti-rule: a source's "readiness later" column is **the
maximum** the readiness compute may use, not the default. The
default for every direct WHOOP-derived input is
`confidence: low`. Promotion to `confidence: medium` requires
an Aaron-tester confirmation line in `FEEDBACK_SUGGESTIONS.md`.
`confidence: high` is reserved and never returned by the
prototype until an explicit doc-commit promotion. Sources
listed as "NEVER eligible" stay that way regardless of how
much data has flowed.

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
coder-thinks-it-works sense) when ALL hold. Updated 2026-05-07
against `CLAUDE-MCP-UNIFICATION-SPEC-04` to add a +1
direct-integration gate AND a unified-MCP-state gate.

1. **P0.1 + P0.2 + P0.3 verified.** Apple Health hub on Aaron's
   iPhone + Health Connect hub on girlfriend's Android each
   surface RHR / HRV / sleep / workouts / active calories with
   correct truth labels. "Polar via hub" label propagation
   audited and clean.
2. **Missing data renders as "no data".** No fabricated zeros,
   no implicit fallbacks. Visible across at least one full day
   per source on both devices. Strings come from
   `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 2.
3. **Nutrition card shows daily totals + targets + history**
   with no coaching language. Apple Health "Nutrition" types
   labelled `imported summary` from hub (when present).
   Cronometer routing follows
   `docs/CRONOMETER_IMPORT_FLOW.md` § 1 — hub-first, no direct
   API.
4. **WHOOP UI honest**: every WHOOP-related card / chip says
   `setup required` (until P1.1+P1.2 ship) or
   `seed/provisional` (within 7 days post-migration). Never
   `live` until P1.3 unblocks.
5. **No Polar Direct / Polar AccessLink label anywhere** until
   `docs/POLAR_ACCESSLINK_PLAN.md` § O.4 promotion conditions
   hold. Even in admin-only diagnostic strings.
6. **Friendly error UI** (commit `a036fd5`) ships in tester
   build for WHOOP / Polar disconnect-vs-no-data distinction.
   Strings come from
   `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 5.3.
7. **Aaron + girlfriend both confirm in writing** that their
   Health tab is honest and useful for daily training. Recorded
   as `approved_done` against an FS-XXX candidate.
8. **+1 direct integration live** beyond the two platform hubs
   (Apple Health + Health Connect already covered by P0.1 /
   P0.2). Acceptable options for the +1 gate, in priority
   order:
   - **WHOOP Direct** (1.4.a + 1.4.b) — preferred. Truth label
     has crossed `seed/provisional` → `live` per
     `docs/WHOOP_DIRECT_SETUP.md` § M.3 conditions
     (≥7 days clean, daily readings, Aaron tester
     confirmation, FS-008 `approved_done`).
   - **WHOOP raw export** (1.4.c) — acceptable substitute if
     Aaron defers FS-008. Truth label stays `imported
     summary`; the gate is "user can upload an export and see
     it surfaced with correct provenance".
   - **Polar AccessLink** (1.5) — acceptable but late;
     follows `docs/POLAR_ACCESSLINK_PLAN.md` outline once
     scoped. Same `≥7 days clean` ladder as WHOOP.
9. **Unified MCP state** — every consumer (ChatGPT
   connector / mobile app admin/dev / control-centre) sees the
   same canonical-store snapshot via the contract in
   `docs/UNIFIED_MCP_PLAN.md` § 15:
   - Public reads return identical priority / blocker / next
     action across `project.get_current_state` /
     `project.get_work_status` / `/api/control_centre`
     (within the 10-min freshness window).
   - Every `mobile.get_*` and `handoff.get_latest` v2 tool
     surfaces the canonical `freshness` envelope shipped in
     commit `8a393b7` (worker MUST be redeployed for this gate
     to clear).
   - Per-source health data exposed via `integrations.*`
     respects the auth model in § 15.2: counts/aggregates
     No-Auth, per-user metrics admin-token only. No personal
     metric leaks via No-Auth.
   - Aaron has confirmed in writing that ChatGPT, mobile
     admin/dev, and control-centre all show the same answer
     to "what is Claude / Codex doing now? what's blocked?"
     when queried within ≤2 minutes of each other.

### 6.2 Grappler Readiness v1

**v1 is hub-first** per
`docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` § "Priority — v1
is hub-first" (updated 2026-05-07 against
`CLAUDE-GRAPPLING-READINESS-HUB-FIRST-PRIORITY-01`). v1
reads only from Apple Health (iOS) and Health Connect
(Android); WHOOP Direct + Polar AccessLink + Bluetooth HR
are explicit v1.5 / v2 enrichments. Hub-routed
WHOOP / Polar data IS in scope under hub provenance
("WHOOP via Apple Health", "Polar via Health Connect").

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

### 6.3 Smallest next implementation bundle + EAS gate

Updated 2026-05-07 against the prompt
`CLAUDE-HEALTH-MCP-UNBLOCK-P1-SPEC-READY-01`.

**FS-008 status: BLOCKED on Aaron approval.** The full
WHOOP OAuth migration — Railway → Cloudflare Worker callback,
WHOOP client secret paste via `wrangler secret put`, WHOOP
developer-console redirect URI update — needs Aaron's explicit
approval before any code lands. Until that approval, FS-008
is the wrong target. The next Codex batch must NOT touch any
WHOOP OAuth wiring.

**Smallest next Codex batch: § 7 Phase 1 mobile audit + small
copy patches** (`PROMPT-ID:
CODEX-HEALTH-NUTRITION-AUDIT-MOBILE-PHASE-1-LABELS-01`). Scope:
audit existing health-tab UI strings + mobile services for
truth-label compliance, propose ≤20 line/file copy patches,
no React redesign, no Worker, no migration, no native rebuild,
no version bump. Anchored to the canonical truth labels in
this doc § 1 + `HEALTH_CONNECTIVITY_TRUTH_SPEC.md` § 3.

This bundle is appropriate **now** because:
- It does not depend on FS-008 (no WHOOP code path touched
  beyond label hygiene).
- It directly serves P0.1 / P0.2 / P0.3 (the per-platform
  reliability gates that block everything else).
- It produces no native code, so no EAS build is implied.
- It requires no Aaron-side action other than reviewing the
  audit list + approving any final copy patches.

**EAS build gate** (extends rule 7 +
`docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build cost control"):
- Codex's most recent commit `c8e9f48 HealthNutrition:
  simplify health tab daily flow` is **NOT** sufficient on its
  own to justify a build. One UX simplification is too small a
  delta to spend an EAS build slot.
- The next EAS build dispatches **only** after ALL hold:
  1. Phase 1 mobile audit completes with patches landed.
  2. At least one other meaningful mobile bundle has shipped
     to main alongside it (e.g. P1.5 Polar-via-hub label
     propagation completing, or P0.3 hub-label leakage audit
     closing).
  3. Agent functional audit confirms the bundle is worthwhile
     to test on-device (rule 7: "Agent confirms the change is
     worthwhile to test on-device").
  4. Aaron explicitly approves the build (rule 7: default is
     no build).
- Health-source phrasing fixes alone never trigger a build per
  the do-not-promote rule (§ 5).

**Aaron's pending decision points** (the prompt asks for
these so they don't drift into Apple Notes — rule 10):
1. Approve / defer FS-008 (WHOOP OAuth migration). Default
   action: defer until Phase 1 audit completes.
2. Approve / decline the Phase 1 audit batch dispatch to
   Codex. Default action: approve — it is docs-and-copy only
   and unblocks P0.
3. After Phase 1 lands, approve / defer the next bundled EAS
   build per the gate above.

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
