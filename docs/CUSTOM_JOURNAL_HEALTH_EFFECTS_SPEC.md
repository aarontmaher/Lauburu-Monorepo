# Custom journal — health-effects spec

The single doc that defines the flexible custom-timeline
journal where users track arbitrary interventions
(medications, peptides, supplements, training changes,
respiratory devices, sleep aids, weight-cut interventions,
custom items) and the app surfaces possible associations with
hub-fed health metrics — never causation, always confidence.
Updated 2026-05-08 against
`CLAUDE-CUSTOM-JOURNAL-HEALTH-EFFECTS-SPEC-01`.

This is **spec only**. No mobile UI implementation, no
migrations, no version bump, no EAS build.

## 0. Two journal surfaces

The Lauburu codebase now has **two distinct journal-like
surfaces**. They serve different needs and MUST NOT be
collapsed:

| Surface | Owns | Granularity | Already shipping |
|---|---|---|---|
| **Daily journal entry** (`apps/mobile/src/store/daily-journal-store.ts`, Codex bundle B2) | today's training intent + mood + free-text context | one row per day | yes — `daily-journal-store.ts` shipped 2026-05-08 |
| **Custom timeline journal** (this spec) | tracked items spanning days/weeks/months with start/stop/dose-change events, plus computed dose-active periods + metric-effect windows | one row per item; many events per item | NO — this spec is the design; FS-018 below |

The two are joined only by date — when a user opens "Today"
they see their daily entry plus the active items from the
custom timeline.

## 1. Schema

Four core tables. All RLS-gated by `auth.uid() = user_id`.

### 1.1 `journal_items`

The tracked thing — a peptide, a medication, a supplement, a
training change, a device, a one-off note. One row per
distinct tracked item per user.

```sql
create table public.journal_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  category text not null,                     -- enum below
  name text not null,                         -- "HCG", "Salbutamol", "Mouth tape", "Push week 3", etc.
  unit text,                                  -- "iu", "mg", "puffs", "mcg", null for non-dose items
  default_dose numeric,                       -- starting dose if any; events may override
  default_frequency text,                     -- "daily", "twice daily", "as needed", "weekly" — free text by design
  may_affect_metrics boolean not null default true,   -- user-set flag: "this could affect health metrics" — opt-out for purely informational notes
  notes text,                                 -- free-text context the user types when creating the item
  source text,                                -- "user", "imported_apple_notes", "imported_csv" — provenance of the row itself
  confidence text not null default 'user_reported',  -- enum below; how reliable the user thinks the data is
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.journal_items enable row level security;
create policy journal_items_self on public.journal_items
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

`category` enum (extensible by doc commit only):
- `medication` — dexamphetamine, amitriptyline, prescription drugs
- `peptide` — HCG, HGH, BPC-157, TB-500, etc.
- `supplement` — creatine, magnesium, vitamins
- `nasal_spray` — saline, decongestant, steroid spray
- `inhaler` — salbutamol, budesonide, Pulmicort
- `sleep_aid` — mouth tape, melatonin, magnesium-glycinate
- `caffeine` — coffee, pre-workout, caffeine pill
- `nutrition_change` — keto, fasting window, weight cut
- `training_change` — push week, deload, technical-only block
- `injury` — injury note with body part + severity
- `pain` — chronic pain track
- `illness` — cold, flu, infection
- `respiratory_treatment` — Airofit session, nasal spirometry, breathing protocol
- `weight_cut_intervention` — sauna, water cut, sodium load
- `surgery` — surgical procedure with date
- `custom` — anything not in the list; free-text `name` becomes the only label

`confidence` enum (how reliable Aaron's records are):
- `user_reported` — Aaron typed it; default
- `prescription_verified` — backed by a prescription record / pharmacy receipt (out of v2 scope but reserved)
- `device_verified` — backed by an Airofit / inhaler app / etc. that wrote a record
- `imported_uncertain` — imported from Apple Notes or CSV and dates are approximate

### 1.2 `journal_events`

Events that change an item's status over time. Each event has
an effective timestamp.

```sql
create table public.journal_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id uuid not null references public.journal_items(id) on delete cascade,
  event_type text not null,                   -- enum below
  effective_at timestamptz not null,          -- when the event takes effect (not when it was logged)
  dose numeric,                               -- nullable; for dose_change events
  unit text,                                  -- mirrors the item's unit; redundant for query convenience
  frequency text,                             -- nullable; for dose_change events that change schedule
  notes text,
  source text,                                -- "user", "imported_apple_notes"
  confidence text not null default 'user_reported',
  created_at timestamptz not null default now()
);

create index idx_journal_events_item_effective on public.journal_events(item_id, effective_at);
alter table public.journal_events enable row level security;
create policy journal_events_self on public.journal_events
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

`event_type` enum:
- `start` — item became active
- `stop` — item ended (no longer in use)
- `dose_change` — dose / frequency changed; new value in the row
- `break_start` — user paused but plans to resume; cleaner semantics than stop+restart
- `break_end` — break ended; item resumes
- `one_off_use` — single-use entry (e.g. "took Panadol once today"); auto-stops same day
- `symptom_note` — symptom observed (e.g. "felt nauseous")
- `training_note` — training observation linked to this item (e.g. "felt strong in roll")
- `injury_note` — injury status update
- `custom` — fallback; `notes` is the only payload

### 1.3 `journal_dose_periods` (computed view)

Materialised view derived from `journal_events`. Lists every
contiguous "this dose was active" period per item. Built by
the readiness compute, NOT user-edited.

```sql
create materialized view public.journal_dose_periods as
select
  i.user_id,
  i.id as item_id,
  i.name,
  i.category,
  -- a period is bounded by start/break_end on the left and stop/break_start on the right
  starts.effective_at as period_start,
  stops.effective_at as period_end,
  starts.dose as dose,
  starts.unit as unit,
  starts.frequency as frequency
from public.journal_items i
join public.journal_events starts on starts.item_id = i.id
  and starts.event_type in ('start', 'break_end', 'dose_change')
left join lateral (
  select e.effective_at, e.event_type
  from public.journal_events e
  where e.item_id = i.id
    and e.effective_at > starts.effective_at
    and e.event_type in ('stop', 'break_start', 'dose_change')
  order by e.effective_at asc
  limit 1
) stops on true;
```

Refresh policy: nightly cron + on-demand when an event is
inserted for an item with active periods.

### 1.4 `metric_effect_windows` (computed view)

Per-item × per-metric window comparison. The output of the
effect-analysis method below. Stored so the UI can render
without recomputing.

```sql
create table public.metric_effect_windows (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id uuid not null references public.journal_items(id) on delete cascade,
  metric text not null,                       -- "rhr", "hrv_rmssd", "sleep_duration_min", "readiness_score", "training_load_acute", etc.
  comparison_kind text not null,              -- "before_after_start", "before_after_stop", "dose_change", "break_window"
  baseline_window_start timestamptz not null,
  baseline_window_end timestamptz not null,
  effect_window_start timestamptz not null,
  effect_window_end timestamptz not null,
  baseline_mean numeric,
  baseline_n int,                             -- sample count
  effect_mean numeric,
  effect_n int,
  delta numeric,                              -- effect_mean - baseline_mean
  delta_pct numeric,                          -- (delta / baseline_mean) * 100
  confidence text not null,                   -- enum below
  confounders text[],                         -- list of overlapping item ids that may also explain the change
  computed_at timestamptz not null default now()
);

alter table public.metric_effect_windows enable row level security;
create policy metric_effect_windows_self on public.metric_effect_windows
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

`confidence` enum on the analysis output:
- `provisional` — too few samples (<7 in either window) OR ≥1 overlapping item with `may_affect_metrics: true`
- `low` — sample sizes adequate but ≥1 overlapping item OR variance ratio (effect σ / baseline σ) > 1.5
- `medium` — sample sizes adequate, no overlapping items, variance ratio ≤1.5
- `high` — **NEVER returned by the prototype.** Reserved for the calibrated future state where Aaron has manually validated ≥10 effect-window readings against his subjective experience.

## 2. Effect-analysis method

For every item × metric pair, the compute produces zero or
more `metric_effect_windows` rows by comparing two windows.
This is the only inference Lauburu does on journal data; it
is **statistical association**, not medical claim.

### 2.1 Window selection

Per `event_type`, the windows are:

| comparison_kind | Trigger event | Baseline window | Effect window |
|---|---|---|---|
| `before_after_start` | `start` event | 14 days ending the day before `effective_at` | 14 days starting at `effective_at` (or until next event on the item) |
| `before_after_stop` | `stop` event | 14 days ending the day before `effective_at` | 14 days starting at `effective_at` |
| `dose_change` | `dose_change` event | 14 days ending the day before `effective_at` | 14 days starting at `effective_at` |
| `break_window` | `break_start` paired with later `break_end` | 14 days before `break_start` | 14 days during the break |

If the user has fewer than 7 samples for a metric in either
window, the window's `confidence` MUST be `provisional` and
`delta` / `delta_pct` MUST NOT be rendered.

### 2.2 Metrics in scope

Metrics computed against (read from
`docs/HEALTH_BACKEND_CONTRACT_FOR_CODEX.md` § 3.1):
- `rhr` (Apple Health / Health Connect resting HR)
- `hrv_rmssd` (when present)
- `sleep_duration_min`
- `sleep_efficiency_pct` (if upstream supplies)
- `readiness_score` (Lauburu's own compute output, not vendor)
- `training_load_acute` (7d rolling load from Lauburu manual + hub workouts)
- `subjective_soreness` (NextDayCheckin slider, 1-10)
- `subjective_mood` (NextDayCheckin slider, 1-10)

NOT in scope (never auto-correlated):
- weight, body fat, lean mass — quarterly cadence, too few samples
- nutrition (kcal / macros) — context, not a readiness output
- blood test / DEXA — quarterly evidence, never auto-correlated against journal items

### 2.3 Confounder detection

For each computed window, the analyser walks
`journal_dose_periods` for the same user and finds any
**other** item with `may_affect_metrics: true` whose period
overlaps the effect window by ≥7 days. Each such overlapping
item is appended to `confounders[]`. If `confounders[]` is
non-empty, the output `confidence` floor drops to `low`.

### 2.4 Output language (UI binding)

The `metric_effect_windows` row drives one user-facing
sentence. The mapping from compute output to text is fixed:

| Confidence | Sentence template |
|---|---|
| `provisional` | "Not enough data yet to compare {metric} before vs after {item}." |
| `low` | "{metric} appeared to {direction} by {abs(delta_pct)}% in the 14 days after {item} started, but {confounders.length} other tracked item(s) overlapped that window — confidence: low." |
| `medium` | "{metric} {direction} by {abs(delta_pct)}% in the 14 days after {item} started ({effect_n} samples) compared to the baseline window. Confidence: medium." |

`{direction}` = `dropped` if delta < 0, `rose` if delta > 0.
`{metric}` is rendered with provenance ("HRV (RMSSD) via
Apple Health", "Resting HR via Health Connect").

Banned phrasings:
- "{item} caused…" (causation)
- "{item} improved…" (judgment)
- "{item} is helping…" (medical claim)
- "Stop taking {item}…" (medical advice)
- Any clinical / diagnostic language.

Allowed framing words: `appeared`, `associated with`, `may
have contributed to`, `correlated`, `coincided with`. The
output never crosses into causation language.

## 3. Beginner UX

Beginner sees one entry point on the Train tab or the daily
journal entry screen:

> **Track something** &nbsp;[ + ]

Tap `+` opens the category sheet:

```
┌─────────────────────────────┐
│ What are you tracking?      │
│                             │
│ • Medication                │
│ • Peptide                   │
│ • Supplement                │
│ • Inhaler / nasal spray     │
│ • Sleep aid                 │
│ • Caffeine                  │
│ • Nutrition change          │
│ • Training change           │
│ • Injury / pain             │
│ • Illness                   │
│ • Respiratory treatment     │
│ • Weight-cut intervention   │
│ • Custom                    │
└─────────────────────────────┘
```

Tap a category → minimal-fields sheet:

```
┌─────────────────────────────┐
│ Name      │ ____________    │
│ Dose (?)  │ ____________    │
│ Started   │ today | pick    │
│ Notes     │ ____________    │
│                             │
│      [ Save & track ]       │
└─────────────────────────────┘
```

Once saved, the item shows on a "What you're tracking" list.
Tap an item → quick actions:

- **Dose changed** → opens dose-change sheet
- **Took a break** → records `break_start`
- **Stopped** → records `stop`
- **One-off use** (for items like Panadol) → records `one_off_use`
- **Note** → free-text symptom / training observation

Beginner default: `may_affect_metrics: true` for every category
except `custom` (which defaults to `false` — unknown).

Beginner does NOT see effect-window analysis. They see only:
"You're tracking 4 things." The analysis surface is veteran
mode.

## 4. Veteran UX

Veteran toggle (existing `isAdminEmail` gate) reveals the
timeline view:

### 4.1 Timeline screen

Horizontal time axis (zoomable: month / quarter / year). Each
tracked item is a swimlane row. Active periods render as
solid bars; breaks render as gapped bars; one-off events
render as dots. Below each item, an inline sparkline of one
toggleable metric (default: `rhr` or `hrv_rmssd` if present)
overlays the same time axis. Tapping a period opens the
period-detail sheet with the corresponding
`metric_effect_windows` rows.

### 4.2 Before / after comparison

For every period start, stop, dose change, or break, the
analysis surface shows:

```
HCG · started 28 Oct · stopped 8 May
─────────────────────────────────────
HRV (RMSSD) via Apple Health
  baseline (14d before): 48 ms (n=12)
  effect   (14d after):  52 ms (n=11)
  delta:                +4 ms (+8%)  ↑
  confidence: low
  ⚠ confounders: HGH (overlapping period)

Resting HR via Apple Health
  baseline (14d before): 58 bpm (n=14)
  effect   (14d after):  56 bpm (n=14)
  delta:                -2 bpm (-3%)  ↓
  confidence: low
  ⚠ confounders: HGH (overlapping period)

Sleep duration via Apple Health
  not enough data yet to compare.
```

Confounder warning is a yellow chip — never red, never
hidden, never silently dropped.

### 4.3 Confounder warning

When ≥1 other tracked item overlaps the analysis window, the
veteran view shows:

```
⚠ Confounders during this window:
  • HGH (started 19 Jan, dose changed 12 Mar)
  • Salbutamol (active throughout)
```

Plain text, sortable by overlap duration. The user reads it
and decides for themselves; Lauburu does not score
confounders.

### 4.4 Apple Notes import wizard

Aaron's example data lives in Apple Notes today. v2 ships an
import wizard:

1. User pastes the Apple Notes block.
2. The app shows a parser preview (best-effort: name + dates
   + dose detected from common patterns like "HCG, started
   28 Oct, dose 1500iu, stopped 8 May").
3. User confirms each parsed row OR edits.
4. Each confirmed row writes one `journal_items` + a `start`
   event (and `stop` if a stop date was parsed).
5. `confidence` = `imported_uncertain` for every row from the
   wizard; user can promote to `user_reported` after edit.

The parser is intentionally conservative — when in doubt, it
asks rather than guessing.

## 5. Readiness integration

The custom journal feeds **context** into Grappling Readiness,
not direct compute inputs. Three integration points:

### 5.1 Confidence modulation

If the readiness compute is about to return `confidence:
medium` for a day, AND there are ≥2 active tracked items with
`may_affect_metrics: true` for that day, the compute caps
confidence at `low` and renders "Multiple tracked items
active — readings may be influenced." This protects Aaron
from over-interpreting a quiet medium reading on a complex
intervention day.

### 5.2 "Why" bullet enrichment

When the readiness compute returns the `why` bullets (top
3 contributing signals), the journal layer adds a fourth
"context" bullet IF a `metric_effect_windows` row with
`confidence: low` or `medium` is the most recent one for any
tracked item active today. Example bullet:

```
• Context: HRV appeared 8% higher in the 14 days after HCG
  started, but HGH overlapped — confidence: low.
```

Hedged language only. Never a recommendation.

### 5.3 Personal athlete memory

Over time the `metric_effect_windows` table builds Aaron's
personal pattern: which items have repeatedly correlated with
which metric directions. Aaron can mark a window
`reviewed_by_user: true` on the veteran timeline; the next
review computes a per-item summary like:

```
HCG (across 3 dose periods, 2 stop events):
  HRV: associated with +5% change (low confidence)
  RHR: associated with -2% change (low confidence)
  Sleep: not enough data
  4 of 5 windows had confounders
```

This is per-user only; never flows to MCP / connector / cross-
user aggregate. The Lauburu backend never compares Aaron's
patterns to another user's.

## 6. Safety rules

These are non-negotiable. Every UI surface, copy variant,
notification, and analysis output respects them.

- **No medical advice.** Lauburu MUST NOT say "you should
  start / stop / change the dose of {item}".
- **No causation claims.** Always "associated with" / "may
  have contributed to" / "appeared to" / "correlated with" /
  "coincided with" — never "caused".
- **No safety inference.** Lauburu MUST NOT comment on
  whether a dose is safe, whether two items interact, or
  whether a condition is concerning. "Talk to your doctor"
  is the only allowed health-action language, and even then
  only on the privacy / disclaimer surface, not in
  per-window analysis copy.
- **No third-party share.** Journal items + events + windows
  are user-scoped. They never appear in MCP / connector /
  control-centre / aggregate analytics. The redactor in
  `cloudflare-worker/src/redactor.ts` (planned) drops any
  string matching item / event names if it appears in a
  bridge-bound field.
- **No clinical thresholds.** "Your HRV dropped below 40 ms"
  is forbidden — no numeric clinical thresholds. Comparisons
  are always to the user's own baseline.
- **No imputation.** When a metric has fewer than 7 samples
  in either window, the analysis returns `provisional` and
  the UI says "not enough data yet to compare". No
  estimated values, no fabricated samples.
- **No confounder hiding.** Every overlapping item with
  `may_affect_metrics: true` MUST be listed. The user reads;
  Lauburu does not pre-rank.
- **No removing user data.** Journal items + events are
  immutable once written, except by the user via the
  veteran timeline edit affordance. No background jobs
  delete journal rows.
- **No exporting journal data via MCP.** `/api/control_centre`
  + every `/mcp/*` tool MUST exclude this data.
  Admin-token-gated tools may surface counts only (e.g.
  "trackedItemsCount: 7") — never names, doses, or windows.

## 7. FS candidate

| Field | Value |
|---|---|
| FS ID | FS-018 |
| Title | Custom timeline journal — flexible tracked items + metric-effect windows |
| Status | candidate, awaiting Aaron approval |
| Lane | 3 (DB schema + per-user storage + privacy boundary) |
| Spec home | `docs/CUSTOM_JOURNAL_HEALTH_EFFECTS_SPEC.md` (this doc) |
| Audit row | extends `HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.13 (Journal uploads) — supersedes that section's scope |
| Roadmap rank | v2 evidence input per `GRAPPLER_READINESS_PROTOTYPE_PLAN.md` § "Evidence input roadmap (v1 / v2 / v3)" |

## 8. Codex handoff

Drop-in for the next Codex batch when Aaron approves FS-018.
This is bundle B2-extended: Codex's existing `daily-journal-store.ts` daily
entry stays untouched; the custom timeline is new surface.

```
PROMPT-ID: CODEX-CUSTOM-JOURNAL-V1-SCHEMA-AND-UI-01
TYPE: CODEX
LANE: Mobile / custom timeline journal (FS-018)

MCP-FIRST: call project.get_current_state.

Reference (read first):
- docs/CUSTOM_JOURNAL_HEALTH_EFFECTS_SPEC.md (this doc) —
  full schema + event types + UX + safety rules.
- docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md § 4 +
  § 5 — confidence labels + missingness copy.
- docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md §
  "Evidence input roadmap (v1 / v2 / v3)" — v2 placement.

Phase 1 scope (this batch):

1. Schema only — write the SQL migration for
   journal_items, journal_events, journal_dose_periods
   (materialised view), and metric_effect_windows. Match
   § 1 verbatim. RLS policies on every table.
2. Mobile store — apps/mobile/src/store/custom-journal-store.ts
   (NEW; do NOT touch daily-journal-store.ts). Local cache
   + Supabase sync. Initial event-type enum + category
   enum lifted from § 1 (no new categories without doc
   commit).
3. Beginner UX — implement § 3 ONLY. Track-something entry
   + category sheet + minimal-fields sheet + tracking
   list with quick actions (dose changed / break /
   stopped / one-off / note). NO timeline view, NO
   effect analysis surface, NO veteran-mode toggle.
4. Apple Notes import wizard — DEFERRED to a later batch.
   Out of scope here.
5. Readiness integration — § 5.1 confidence modulation
   only. § 5.2 / § 5.3 deferred (require effect-window
   compute, which is a separate batch).
6. Effect-window analyser — DEFERRED to a separate batch
   after the schema lands.
7. Privacy: every item / event / window MUST be
   user-scoped via RLS. Worker MUST NOT expose any field
   under No-Auth tools. /api/control_centre admin tool
   MAY include trackedItemsCount only.
8. NO React redesign of unrelated screens. NO Worker
   route addition. NO native rebuild. NO version bump.
   NO EAS build.
9. Status report opens with rule-12 three-field block AND
   rule-13 three-section split AND rule-14 parallel-priority
   freshness notes.
10. Status sequence MUST be the four-string ladder per
    rule 8.

Anti-rules (lifted from § 6 — repeat verbatim in any
generated copy):
- No medical advice.
- No causation claims.
- No safety inference.
- No clinical thresholds.
- No imputation.
- No confounder hiding.
- No exporting journal data via MCP.

Output:
- changed files (SQL migration + mobile store + beginner
  UI screens; NO daily-journal-store edits)
- four-status compliance per FS-018
- recommendation for Phase 2 (timeline + effect-window
  analyser + Apple Notes import)
- explicit statement: this batch did NOT request, recommend,
  or trigger an EAS build
- rule-12 three-field block + rule-13 three-section split +
  rule-14 parallel-priority status notes
```

## 9. Anti-rules (umbrella)

- **No collapsing daily entry and custom timeline.** They
  are two surfaces with different needs.
- **No auto-promotion from imported_uncertain to
  user_reported.** Only the user clicks confirm.
- **No `confidence: high` from the analyser**, ever, in v2.
  Reserved for the post-calibration state.
- **No journal data on No-Auth MCP tools.** Admin tools may
  surface counts only. Per-item names / doses / windows
  stay off MCP.
- **No automatic dose recommendations** based on observed
  windows. Even with ten years of data, Lauburu MUST NOT
  suggest "try 1500iu vs 2000iu of HCG" — that crosses into
  prescription territory.
- **No cross-user pattern matching.** "Other users on HCG
  saw…" is permanently out of scope.
- **No deletion of journal data without explicit user
  action.** No background cleanup jobs.

## 10. Cross-references

- `docs/HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.13 —
  parent journal entry; this spec supersedes it for the
  custom timeline use case.
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` §
  "Evidence input roadmap (v1 / v2 / v3)" — v2 placement
  + parallel bundle B2 reference.
- `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` —
  confidence label format + missingness strings.
- `docs/PRIVACY.md` — per-user storage rules.
- `docs/CONNECTOR_SECURITY_MODEL.md` — admin-token gate
  + redactor expectations.
- `docs/UNIFIED_MCP_PLAN.md` § 15 — auth model the journal
  schema MUST honour (no public-write tool ever).
- `docs/FEEDBACK_SUGGESTIONS.md` FS-018 (added by this
  commit).
