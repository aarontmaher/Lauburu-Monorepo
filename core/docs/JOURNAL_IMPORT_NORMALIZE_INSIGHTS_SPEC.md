# Journal import, term normalization, macro ratios, personal insights — spec

The doc that extends the existing FS-018 custom-journal schema
(`docs/CUSTOM_JOURNAL_HEALTH_EFFECTS_SPEC.md`) with: import paths
from external journal-shaped sources, a term-normalization layer
that asks the user to confirm canonical names, a macro-ratio
tracking layer over food/macros entries, and a cautious
personal-pattern engine that surfaces association (never
causation) windows over time. Updated 2026-05-08 against
`CLAUDE-JOURNAL-IMPORT-NORMALIZE-MACRO-INSIGHTS-01`.

This is **spec only**. No mobile UI implementation, no
migrations, no version bump, no EAS build.

## 0. Relationship to FS-018

FS-018 (commits `79d2a1e` + `9a6fc68`) shipped:
- `journal_items` (registry) + `journal_events` (timeline) +
  `journal_dose_periods` (computed view) +
  `metric_effect_windows` (analysis output) Supabase schema.
- `apps/mobile/src/store/custom-journal-store.ts` with the
  category + event-type enums.
- Beginner UX for "Track something" → category sheet →
  minimal-fields sheet → tracking list.

This spec (FS-020) **extends** that schema; it does NOT
duplicate or replace it. New tables / columns are additive.
The same RLS-gated, user-scoped contract holds.

## 1. Two-track design

Aaron's prompt distinguishes between two kinds of journal
data: **medication / supplement / peptide / training-context
items** (already covered by FS-018's `journal_items`) and
**daily nutrition macros**. They share the same import +
normalization layer but diverge at the storage layer:

- **Track A — discrete tracked items** — extends `journal_items`
  + `journal_events`. Each row is a thing the user is tracking
  over time (a peptide, a medication, a respiratory device).
- **Track B — daily nutrition macros** — new
  `nutrition_daily_log` table, one row per (user_id, date).
  This is NOT a tracked-item — macros are a per-day total, not
  a discrete intervention.

The import wizard processes both tracks; the parser routes
each entry to the right table based on shape.

## 2. New schema

Three additions, all RLS-gated by `auth.uid() = user_id`.

### 2.1 `journal_term_normalizations`

Canonical-term registry with aliases + user confirmation.
Built up over time as users import unfamiliar terms.

```sql
create table public.journal_term_normalizations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  raw_text text not null,                     -- exact text as imported (lowercased + trimmed)
  canonical_term text not null,               -- "BPC-157", "HCG", "amitriptyline", etc.
  category text not null,                     -- enum from FS-018 § 1.1
  aliases text[] not null default array[]::text[], -- additional shorthand variants the user accepts
  user_confirmed boolean not null default false,   -- false until the user taps "Yes, that's right"
  needs_user_confirmation boolean not null default true, -- false for trivial passes (exact-match in shared dictionary)
  confidence text not null default 'low',     -- 'low' | 'medium' | 'high' (NEVER returned as 'high' until user_confirmed)
  source text not null default 'user',        -- 'user' | 'imported_paste' | 'imported_file' | 'shared_dictionary'
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, raw_text)
);

alter table public.journal_term_normalizations enable row level security;
create policy journal_term_normalizations_self on public.journal_term_normalizations
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

A separate **shared dictionary** (read-only, no user-private
data) lives at `cloudflare-worker/src/data/journal-canonical-terms.ts`
as a static const. It seeds the normalizer with public
canonical names + obvious aliases (`bpc` / `bpc157` / `BPC-157`,
`hgh` / `growth hormone`, `hcg`, `amitriptyline`,
`pulmicort` / `budesonide`, etc.). The shared dictionary is
**public-safe** — it contains drug / peptide / supplement
common names that are public knowledge, not user data.

Personalised aliases land in the per-user table only.

### 2.2 `nutrition_daily_log`

One row per (user_id, date) with macro totals + derived
ratios.

```sql
create table public.nutrition_daily_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  date date not null,
  protein_g numeric,
  carbs_g numeric,
  fat_g numeric,
  fiber_g numeric,
  calories integer,
  bodyweight_kg numeric,                      -- optional; required for protein_g_per_kg
  source text not null,                       -- 'manual' | 'imported_csv' | 'imported_paste' | 'cronometer_via_hub' | 'apple_health' | 'health_connect'
  source_provenance text,                     -- e.g. "Cronometer via Apple Health"
  notes text,
  raw_import_ref uuid references public.journal_imports(id) on delete set null, -- back-pointer to original import
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, date, source)
);

alter table public.nutrition_daily_log enable row level security;
create policy nutrition_daily_log_self on public.nutrition_daily_log
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

Derived ratios (`protein_pct`, `carbs_pct`, `fat_pct`,
`protein_g_per_kg`) are computed on read, NOT stored — that
prevents drift if the user corrects raw numbers later.

### 2.3 `journal_imports`

Audit / provenance row per import operation. Lets the user
see "this entry came from this paste on this date".

```sql
create table public.journal_imports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  source_kind text not null,                  -- 'paste' | 'csv_file' | 'apple_notes' | 'whoop_export' | 'cronometer_export' | 'other_file'
  source_filename text,                       -- nullable; only set for file imports
  raw_size_bytes integer not null,            -- size of the input (paste length or file bytes)
  raw_hash text not null,                     -- sha256 of input (allows dedupe + privacy: stored hash, not raw text)
  parsed_count integer not null default 0,    -- number of rows parsed
  imported_count integer not null default 0,  -- number actually accepted (after user confirm)
  skipped_count integer not null default 0,   -- number user skipped
  notes text,                                 -- user's freeform tag for this import
  status text not null default 'preview',     -- 'preview' | 'applied' | 'partial' | 'cancelled'
  created_at timestamptz not null default now(),
  applied_at timestamptz
);

alter table public.journal_imports enable row level security;
create policy journal_imports_self on public.journal_imports
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

The `raw_hash` (not raw text) lets the importer warn "you've
already imported this exact paste" without storing the
sensitive raw input forever.

## 3. Import UI flow

Single entry point: **Track something → ⋮ → Import**.

### 3.1 Source selection sheet

```
┌────────────────────────────────┐
│ Import journal data            │
│                                │
│ • Paste text                   │
│ • Pick CSV file                │
│ • WHOOP export (CSV/zip)       │
│ • Cronometer export (CSV)      │
│ • Apple Notes block (paste)    │
│                                │
│ [ Cancel ]                     │
└────────────────────────────────┘
```

### 3.2 Paste / file → parser preview

After the user pastes or picks a file:

```
┌────────────────────────────────┐
│ Preview · 14 rows parsed       │
│                                │
│ ✓ HCG 1500iu · started 28 Oct  │
│   2024 · stopped 8 May 2026    │
│   Category: peptide            │
│   ⚠ Confirm "HCG" canonical    │
│                                │
│ ✓ HGH 2iu · started 19 Jan     │
│   2025 · dose change 14 Mar    │
│   Category: peptide            │
│   ⚠ Confirm "HGH" canonical    │
│                                │
│ ⚠ "peptides" too broad —       │
│   please specify which one     │
│                                │
│ ✓ Salbutamol 2 puffs as        │
│   needed · started Apr 2024    │
│   Category: inhaler            │
│                                │
│ … 10 more …                    │
│                                │
│ Skip: 1   Edit: 0   Confirm: 13│
│                                │
│ [ Skip unknown ] [ Cancel ]    │
│ [ Import 13 confirmed ]        │
└────────────────────────────────┘
```

User can:
- Tap any row to edit (date / dose / canonical term / category).
- Tap "Skip unknown rows" to import only the rows that parsed
  cleanly without the broad-term warnings.
- Tap "Cancel" to discard.
- Tap "Import N confirmed" to write the rows to
  `journal_items` + `journal_events` (or `nutrition_daily_log`
  for macros) + a single `journal_imports` audit row.

**Truth labels on each row**:
- ✓ green checkmark — parsed cleanly + canonical term known.
- ⚠ amber warning — needs user confirmation (canonical term
  ambiguous OR new alias).
- ✗ red — could not parse; will be skipped unless user edits.

### 3.3 Term-confirmation modal

When the parser hits an unknown term:

```
┌────────────────────────────────┐
│ Did you mean…                  │
│                                │
│ ◉ BPC-157 (peptide)            │
│ ○ Type a different term:       │
│   ____________________         │
│                                │
│ [ Confirm ]   [ Skip row ]     │
└────────────────────────────────┘
```

User-confirmed terms write to `journal_term_normalizations`
with `user_confirmed: true`. Future imports auto-recognise.

## 4. Parser MVP

The parser is a small, deterministic state machine. NO LLM
calls in v1. Handles five common shapes:

### 4.1 Apple Notes / pasted text

Free-form lines. Heuristics:
- A line with a recognised canonical-term match (case-
  insensitive, alias-aware) → tracked item.
- Numeric tokens with units (`1500iu`, `2mg`, `2 puffs`) → dose.
- Date tokens (`28 Oct`, `28/10/2024`, `started Oct 28`,
  `stopped 8 May`) → start / stop event.
- Comma-separated dose changes → multiple `dose_change`
  events on the same item.
- Lines starting with `#`, `//`, or `[skip]` → skipped.

Aaron's example block parses cleanly:

```
HCG started 28 Oct 2024, dose 1500iu, dose changed to 2000iu 12 Jan, stopped 8 May 2026
HGH started 19 Jan 2025, dose 2iu, dose changed to 1iu time 14 Mar 2025
BPC-157 / TB-500 cycle Apr–Jun 2025
Salbutamol 2 puffs as needed
Pulmicort daily morning
mouth tape started Aug 2025
dexamphetamine 5mg started 12 Nov 2024
amitriptyline 25mg, dose changed several times
```

Each line produces 1 item + 1+ events.

### 4.2 WHOOP export (CSV / zip)

WHOOP's "Export Data" produces a CSV with date / sleep /
recovery / strain columns. The importer:
- Routes WHOOP CSV rows to `manual_imports` (existing FS-014
  schema) with `truth_label: 'imported summary'` — NOT to
  `journal_items` / `nutrition_daily_log`.
- Out of scope for FS-020's tracked-items schema.
- Detected by filename heuristic (`*whoop*`) or column header
  (`recovery_score, hrv, sleep_efficiency`).

### 4.3 Cronometer export (CSV)

Cronometer's daily-export CSV has columns: `Date, Energy
(kcal), Carbs (g), Fat (g), Protein (g), …`. The importer:
- Routes Cronometer CSV rows to `nutrition_daily_log` with
  `source: 'imported_csv'` + `source_provenance: 'Cronometer
  CSV export'`.
- One row per date.
- Detected by filename (`*cronometer*`) or columns matching
  the Cronometer template.

### 4.4 Generic CSV

Free-form CSV. Parser tries to match column headers to known
fields:
- Date columns: `date / day / when / timestamp`
- Item columns: `name / item / what / drug / supplement`
- Dose columns: `dose / amount / mg / iu / puffs`
- Macro columns: `protein / carbs / fat / kcal / calories`

Unrecognised columns are surfaced in the preview as "skip
unknown columns".

### 4.5 Free-text daily log

A single multi-line paste of "today I felt X and took Y mg
of Z". Parser splits by newline, tries the same heuristics
as Apple Notes. Higher proportion of `⚠ confirm` rows
expected because freeform text is noisier.

## 5. Term normalization

Two-tier lookup:

### 5.1 Shared dictionary (read-only, public-safe)

`cloudflare-worker/src/data/journal-canonical-terms.ts` lists
~150 canonical terms with aliases. Public-safe by design —
contains generic drug / peptide / supplement names everyone
recognises, not user-specific data. Examples:

```ts
export const JOURNAL_CANONICAL_TERMS: ReadonlyArray<{
  canonical: string;
  category: JournalItemCategory;
  aliases: readonly string[];
  needsConfirmation: boolean;
}> = [
  { canonical: 'BPC-157', category: 'peptide', aliases: ['bpc', 'bpc157', 'bpc 157'], needsConfirmation: true },
  { canonical: 'TB-500', category: 'peptide', aliases: ['tb500', 'tb 500', 'thymosin beta-4'], needsConfirmation: true },
  { canonical: 'HGH', category: 'peptide', aliases: ['growth hormone', 'somatropin', 'human growth hormone'], needsConfirmation: true },
  { canonical: 'HCG', category: 'peptide', aliases: ['human chorionic gonadotropin'], needsConfirmation: true },
  { canonical: 'amitriptyline', category: 'medication', aliases: ['endep', 'elavil'], needsConfirmation: true },
  { canonical: 'salbutamol', category: 'inhaler', aliases: ['ventolin', 'albuterol', 'asmol'], needsConfirmation: false },
  { canonical: 'budesonide', category: 'inhaler', aliases: ['pulmicort', 'rhinocort'], needsConfirmation: false },
  { canonical: 'creatine', category: 'supplement', aliases: ['creatine monohydrate'], needsConfirmation: false },
  // ... ~140 more
];
```

`needsConfirmation: true` for medications + peptides + HCG /
HGH (anything sensitive enough that the parser should NEVER
guess silently). `needsConfirmation: false` for safe
supplements + common over-the-counter items.

### 5.2 Per-user table (per § 2.1)

`journal_term_normalizations` rows accumulate user-specific
aliases over time. After confirming "BPC-157" once, all
future "bpc 157" / "bpc" pastes auto-match without prompting.

### 5.3 Lookup order

1. Per-user table where `user_id = auth.uid() AND raw_text =
   normalized_input` (lowercased + trimmed).
2. Shared dictionary canonical / aliases.
3. Fuzzy match (Levenshtein distance ≤ 2) against shared
   dictionary canonical names — surface as "Did you mean…?"
   prompt.
4. Otherwise: `⚠ Unknown term — please clarify`.

### 5.4 Privacy

- Per-user terms NEVER flow to MCP / control-centre / shared
  KB / cross-user aggregate.
- Shared dictionary updates require a doc commit + Aaron
  approval (Lane-3 batch). New terms can come from "Aaron
  noticed several testers typed X" — never from a script
  scraping user data.
- Adding a per-user term to the shared dictionary requires
  Aaron approval + the user's explicit consent.

## 6. Research / background hook (Phase 4 placeholder)

Architecture only; NO live research from the mobile app in
v1.

When the user taps a canonical term in their tracked-items
list, the UI offers a **"Background"** disclosure:

```
[ Background ]
  General information about BPC-157.
  General background only — does not determine what is safe
  for you, and does not interpret your personal data.
  • What it is:        peptide, body protection compound 157
  • Common claims:     gut healing, tissue repair (claims, not
                       verified personal effect)
  • Common dosing:     varies; check with a clinician
  • Sources:           [ link 1 ] [ link 2 ]
                       (NOT medical advice)
```

This content lives in a static, server-side
`cloudflare-worker/src/data/journal-research-snippets.ts`
file (or a Supabase `journal_research_snippets` table for
larger volumes). Per term: `summary` + `common_claims` +
`source_links` + a mandatory `disclaimer`. **Never** mixes
in the user's own observations.

UI must always render the three sections separately:

- General background (this section, public, sourced)
- Your own observations (per-user; pulled from
  `metric_effect_windows`)
- Unknown / insufficient evidence

Anti-rule: NO copy that says "This will help you" / "It is
safe for you" / "You should". Always "associated with" /
"general claim" / "not enough data" / "talk to a clinician".

## 7. Macro tracking + insights

### 7.1 Daily macro card

Mobile UI surface (Train tab → Nutrition → daily summary, OR
within the existing `NutritionCard`):

```
Today
  Protein   124 g    27%
  Carbs     215 g    48%
  Fat        62 g    25%
  Calories  1,840

  Protein per kg: 1.6 g/kg (bodyweight 78 kg)

  Source: Cronometer via Apple Health
```

Empty / partial state surfaces honestly:

```
Today
  Protein   — not logged
  Carbs     — not logged
  Fat       — not logged
  Calories  — not logged

  Tap to log meals, or import from Cronometer / CSV
```

### 7.2 Macro derived ratios

Computed on read:

```ts
function deriveRatios(row: NutritionDailyLog): Ratios | null {
  const { protein_g, carbs_g, fat_g, bodyweight_kg } = row;
  if (protein_g == null || carbs_g == null || fat_g == null) return null;
  const protein_kcal = protein_g * 4;
  const carbs_kcal = carbs_g * 4;
  const fat_kcal = fat_g * 9;
  const total_kcal = protein_kcal + carbs_kcal + fat_kcal;
  if (total_kcal === 0) return null;
  return {
    protein_pct: protein_kcal / total_kcal,
    carbs_pct: carbs_kcal / total_kcal,
    fat_pct: fat_kcal / total_kcal,
    protein_g_per_kg: bodyweight_kg ? protein_g / bodyweight_kg : null,
  };
}
```

NOT stored — derived live. If user corrects the raw numbers,
ratios update without a migration.

### 7.3 Macro insights

After ≥7 days of logged data:

```
Across your last 14 days:
  • Higher protein days were associated with +3% better
    perceived sleep (low confidence — 14 observations).
  • Lower carbs days had no observable association with
    next-day RHR (not enough data yet).
```

Anti-rule language (mandatory):
- "associated with" — never "caused"
- "low confidence" — when n < 14 OR confounders present
- "not enough data yet" — when n < 7
- "no observable association" — when correlation < 0.2 AND n
  ≥ 14
- "needs more observations" — generic fallback
- NEVER: "you should eat more protein" / "your fat intake is
  too high" / "X is causing Y"

## 8. Personal pattern engine

Extends FS-018's `metric_effect_windows` analysis. Adds:

### 8.1 Window sets

Per tracked item OR macro day:
- **Same-day**: metric on day N matched to journal day N.
- **Next-day**: metric on day N+1 matched to journal day N
  (e.g. did macros yesterday correlate with sleep tonight).
- **Rolling 3-day**: average metric over [N-2, N] vs average
  intervention over [N-2, N].
- **Rolling 7-day**: average over [N-6, N].

### 8.2 Confidence scoring

| Tier | Sample size | Confounders | UI label |
|---|---|---|---|
| `provisional` | n < 7 in either window | any | "Not enough data yet — needs more observations" |
| `low` | n ≥ 7, < 14 | OR ≥1 confounder | "Low confidence — initial observation" |
| `medium` | n ≥ 14 | AND 0 confounders | "Medium confidence — repeated observation" |
| `high` | RESERVED | RESERVED | NEVER returned by prototype until calibration window + Aaron approval |

### 8.3 Baseline comparison

Always compare against the **user's own baseline**, never a
population norm. "Your sleep on protein-high days vs your
sleep on protein-low days" — never "your sleep vs average
person's sleep".

### 8.4 Confounder detection

Re-uses FS-018's confounder logic: walks
`journal_dose_periods` for overlapping items with
`may_affect_metrics: true`. If any other tracked item
overlaps the analysis window by ≥7 days, the confidence
floor drops one tier.

### 8.5 No safety inference

The engine NEVER says:
- "You should stop X"
- "X is making Y worse"
- "X is dangerous"
- "Talk to your doctor about X" (unless the user explicitly
  taps a `Concerned?` affordance, which surfaces a generic
  "Discuss with a clinician" link — no per-item inference)

The engine DOES say:
- "X day-to-day pattern: associated with +3% Y"
- "Across N observations of X, no consistent direction in Y"
- "Not enough data yet to compare"

## 9. Cross-user aggregate (Phase 7 — DESIGN ONLY)

Out of MVP scope. Designed here to lock in the privacy model
before any code touches it.

### 9.1 Constraints

- **Opt-in only.** A new `share_to_aggregate` flag per item;
  default `false`.
- **Minimum cohort: ≥50 users** with the same canonical term
  before any aggregate query returns data.
- **No per-user attribution** in aggregate output. Worker
  must aggregate at SQL layer; mobile clients see only
  cohort-size + aggregate stats.
- **No medication / sensitive items.** Aggregate is opt-out
  by category (e.g. `supplement` + `nutrition_change` +
  `training_change` are eligible by default; `medication` +
  `peptide` + `injury` + `illness` + `surgery` are NEVER
  aggregable, even with opt-in).
- **No timestamps with hour-level precision.** Only
  date-bucketed.
- **No co-occurrence with other items.** Aggregate queries
  cannot return "users who took X also took Y" — that's
  per-user-traceable.

### 9.2 Aggregate UI (when shipped, not now)

```
Cohort insight (opt-in, anonymised)
  In a cohort of 73 users tracking creatine, protein-per-kg
  was on average 0.2 g/kg higher on the same days.

  This is statistical only. Not personalised. Not medical.
  [ Hide this ]
```

Never says "Users who took X had better Y." Never says "You
should follow the cohort." Aggregate is informational
context, not coaching.

### 9.3 Schema (deferred)

```sql
-- DEFERRED to a separate FS-XXX once Aaron approves the
-- privacy model + cohort thresholds.
create table public.journal_aggregate_optins ( ... );
create materialized view public.journal_aggregate_safe ( ... );
```

## 10. FS candidate

| Field | Value |
|---|---|
| FS ID | FS-020 |
| Title | Journal import + term normalization + macro ratio + personal insights (extends FS-018) |
| Status | candidate, awaiting Aaron approval |
| Lane | 3 (DB schema + per-user storage + privacy boundary + new UI surface) |
| Spec home | `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md` (this doc) |
| Roadmap rank | post-FS-018 Phase 1 (custom-journal-store already shipped); v2 evidence input per `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` § "Evidence input roadmap" |

Sub-batches (each its own commit):
- **B-20a**: Supabase migration — `journal_term_normalizations`
  + `nutrition_daily_log` + `journal_imports` tables; RLS
  policies on each.
- **B-20b**: Worker — `cloudflare-worker/src/data/journal-canonical-terms.ts`
  (~150 entries) + `cloudflare-worker/src/data/journal-research-snippets.ts`
  (~30 entries minimum); contract test that asserts no
  user-private data leaks into either file.
- **B-20c**: Mobile parser — `apps/mobile/src/services/journal-import-parser.ts`
  with the five shapes from § 4. Pure functions; full unit-
  test coverage.
- **B-20d**: Mobile UI — Track Something → ⋮ → Import sheet
  + preview screen + term-confirm modal. NO research
  surface yet.
- **B-20e**: Mobile macro card — daily macros + derived
  ratios + honest empty-state. Lives within existing
  `NutritionCard` if possible (extend, don't duplicate).
- **B-20f**: Personal pattern engine — extend FS-018's
  `metric_effect_windows` with the four window sets +
  confidence scoring.
- **B-20g**: Research-background disclosure — surfaces the
  static snippets behind the **"Background"** disclosure on
  any tracked item.
- **B-20h** (DESIGN-ONLY, defer): aggregate cross-user
  insights. Spec only; no code lands.

## 11. Codex handoff

Single drop-in for B-20a + B-20b paired (smallest safe Worker-
adjacent batch first; Aaron approves before B-20c-h).

```
PROMPT-ID: CODEX-FS020-JOURNAL-IMPORT-SCHEMA-AND-DICTIONARY-01
TYPE: CODEX
LANE: Supabase migration + Worker static dictionary

MCP-FIRST: call project.get_current_state. Bridge → Supabase
direct upsert is LIVE; use bridge:snapshot for end-of-task
cadence per rule 12.

Reference (read first):
- docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md (this doc)
  — full schema + parser + insights model.
- docs/CUSTOM_JOURNAL_HEALTH_EFFECTS_SPEC.md (FS-018) — the
  parent journal schema this extends.
- docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md § 4 —
  confidence labels reuse the same provisional / low / medium
  / (high reserved) ladder.

Phase 1 scope (B-20a + B-20b paired):

1. supabase/migrations/0006_journal_imports_macros_terms.sql
   (NEW). Three tables per § 2 of the spec:
   - journal_term_normalizations (RLS by auth.uid())
   - nutrition_daily_log (RLS by auth.uid())
   - journal_imports (RLS by auth.uid())
   Add indexes on (user_id, date) for nutrition_daily_log and
   (user_id, raw_text) for journal_term_normalizations.
   DO NOT touch existing 0005 FS-018 tables.

2. cloudflare-worker/src/data/journal-canonical-terms.ts (NEW).
   ~150 entries per § 5.1. Public-safe by design — only
   generic drug / peptide / supplement common names, NO
   user data. Categories MUST match FS-018 § 1.1 enum.

3. cloudflare-worker/src/data/journal-research-snippets.ts
   (NEW). ~30 entries minimum: HCG, HGH, BPC-157, TB-500,
   amitriptyline, salbutamol, budesonide, creatine, mouth
   tape, dexamphetamine, Pulmicort, common peptides,
   common supplements. Each entry: summary + common claims
   + source_links + mandatory disclaimer. NO personal
   medical advice. NO causation claims. NO "this will help
   you" copy.

4. cloudflare-worker/test/test-journal-canonical-terms.ts
   (NEW). Asserts:
   - All canonical terms have a category from the FS-018
     enum.
   - All needsConfirmation: true entries are in
     [medication, peptide, inhaler, sleep_aid].
   - No user-private text appears (per-pattern secret scan
     + a list of forbidden personal-name placeholders).
   - All aliases are lowercase + trimmed.
5. cloudflare-worker/test/test-journal-research-snippets.ts
   (NEW). Asserts:
   - All entries have summary + common_claims +
     source_links + disclaimer.
   - No "you should" / "this will help" / "is safe" /
     "is dangerous" strings (banned-phrase regex).
   - All source_links use https:// (no http://).

DO NOT in this batch:
- Mobile UI changes (parser, sheet, preview, modal) —
  separate B-20c + B-20d.
- macro card UI — separate B-20e.
- Pattern engine / metric_effect_windows extension —
  separate B-20f.

Anti-rules (verbatim):
- No medical advice.
- No causation claims.
- No safety inference.
- No clinical thresholds.
- No "you should" / "this will help".
- No user-private data in shared dictionary or research
  snippets.
- No public-write tools.
- No EAS build.

Verification:
- cd cloudflare-worker && npx tsc --noEmit clean
- npm run rules:test PASS
- npm run mcp:test:public-redaction PASS
- npm run bridge:snapshot at end-of-task

Status report opens with rule-12 three-field block + rule-13
three-section split + rule-14 parallel-priority freshness
notes. Status sequence: "Implementation-complete, awaiting
Agent functional confirmation".

Output:
- changed files (3 NEW + 2 NEW tests)
- four-status compliance per FS-020
- recommendation for B-20c (parser) timing
- explicit no-EAS-build statement
- commit SHA
```

## 12. Anti-rules (umbrella, applies to every sub-batch)

- **No medical advice.** Anywhere. Including disclaimers, the
  research-background disclosure, the term-confirmation
  modal, the import preview rows, the macro insights, and
  the pattern-engine output. The only allowed health-action
  language is "talk to a clinician" — and only when the
  user explicitly taps a `Concerned?` affordance.
- **No causation claims.** Always "associated with" /
  "appeared alongside" / "coincided with" / "correlated".
- **No safety inference.** Never comment on whether a dose /
  combination / duration is safe.
- **No clinical thresholds.** "Your protein is below X g/kg"
  is forbidden — comparisons are always to the user's own
  baseline.
- **No imputation.** Missing data stays missing.
- **No cross-user leakage.** Per-user tables are RLS-gated;
  shared dictionary + research snippets are public-safe by
  construction.
- **No exporting journal data via No-Auth MCP.**
  `integrations.get_overview` may surface counts only;
  per-item names / doses / observations stay off MCP.
- **No deletion of user journal data without explicit user
  action.** No background cleanup jobs.
- **No `confidence: high`** from the engine, ever, in v1.
- **No auto-promotion of imported_uncertain to user_confirmed**
  in `journal_term_normalizations`.
- **No silent term-canonical updates.** Adding a new shared-
  dictionary entry is a doc commit + Aaron approval.

## 13. Cross-references

- `docs/CUSTOM_JOURNAL_HEALTH_EFFECTS_SPEC.md` (FS-018) — the
  parent schema this extends.
- `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` —
  confidence labels + missingness strings.
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` § "Evidence
  input roadmap" — v2 placement.
- `docs/CRONOMETER_IMPORT_FLOW.md` — Cronometer hub-first
  contract; the CSV-import path here is a fallback when the
  hub doesn't carry the data.
- `docs/NUTRITION_TRACKING_PLAN.md` — nutrition is context,
  not a primary readiness signal.
- `docs/FS021_HEALTH_INPUTS_EXPANSION_SPEC.md` — queued extension
  for lactate manual/CSV inputs, Daily Dozen-style checklist context,
  and nutrition/recovery association metrics. It reuses FS-020 parser
  privacy rules and stays context-only until Aaron approves a batch.
- Macro insights are personal observations only, never coaching.
- `docs/PRIVACY.md` — per-user storage rules.
- `docs/UNIFIED_MCP_PLAN.md` § 15 — auth model the new
  tables MUST honour.
- `docs/FEEDBACK_SUGGESTIONS.md` FS-020 (registered by this
  commit).
