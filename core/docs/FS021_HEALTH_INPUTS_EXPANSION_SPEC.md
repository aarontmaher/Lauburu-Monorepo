# FS-021 — Lactate, Daily Dozen-style checklist, and nutrition/recovery patterns

Status: candidate, queued behind the active Health connectivity
installed-device QA gate, FS-019 native iPhone control centre, and
FS-020 parser confirmation/UI handoff.

This spec expands health inputs without changing the current release
gate. It is documentation and test scaffolding only until Aaron
approves a focused implementation batch.

## Safety rules

- No medical advice.
- No causation claims.
- No "lactate means you are recovered/fatigued."
- No clinical interpretation.
- Lactate is training/performance context only.
- Daily Dozen-style checklist data is nutrition habit context only.
- Use "associated with", "appeared alongside", "may correlate with",
  and confidence labels only.
- Private journal, nutrition, lactate, checklist, and health data must
  be user-scoped.
- Shared knowledge bases must not contain private user data.
- Cross-user insights require opt-in, anonymization, and minimum cohort
  rules before any implementation.

## 1. Lactate testing support

### Phase 1 — manual first

Manual lactate entry is the first supported path:

- date/time
- mmol/L
- test protocol
- stage/workload
- heart rate
- RPE
- timing relative to training
- source
- confidence
- notes

Copy guardrail:

> Lactate is training context. It does not diagnose recovery, fatigue,
> fitness, or health status.

### Phase 2 — CSV/import

CSV import can map rows into `lactate_measurements` with a raw import
reference. The parser should accept unknown columns without failing and
show them in preview as skipped/unsupported.

### Phase 3 — BLE/device investigation

Device paths are research-only until protocol details are confirmed:

- Lactate Scout Sport/4: BLE features and HR-monitor linkage exist,
  but open mobile integration needs protocol confirmation.
- Lactate Plus: treat as manual/CSV unless Bluetooth support is
  proven.
- Lactate Express: designed for mesics Blood Glucose and Lactate Meter;
  threshold/diagnostic models must not be interpreted clinically by
  this app.
- IDRO: emerging/niche continuous lactate sensor/app path; research
  only until vendor integration is proven.

No UI may label BLE lactate as live until pairing, permissions, data
read, and privacy behavior are proven in code.

## 2. Daily Dozen-style checklist

Daily Dozen-style tracking is a manual checklist/food diary concept.
Do not assume an official app export or API.

Suggested categories are configurable labels, not prescriptions:

- beans/legumes
- berries
- other fruit
- cruciferous vegetables
- greens
- other vegetables
- flax/chia
- nuts/seeds
- spices/herbs
- whole grains
- beverages
- exercise/movement
- custom

Each row records completion/count context for a single user/day. The
app may later compare checklist completion with training and recovery
context using association-only language.

## 3. Nutrition/recovery pattern layer

Allowed context metrics:

- macro ratios
- protein/carbs/fat grams
- fiber grams
- calories
- carb timing around training
- Daily Dozen-style checklist completion
- training session load/RPE
- subjective journal/check-in context
- hub-fed sleep/resting HR/HRV when available

The layer may say:

> Higher carb timing completion appeared alongside better subjective
> session notes in this window. Low confidence.

The layer must not use direct cause wording about recovery,
fatigue, health, or training outcomes.

## 4. Data model proposal

These are proposed tables, not applied migrations in this batch.

```sql
create table public.lactate_measurements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  measured_at timestamptz not null,
  lactate_mmol_l numeric not null check (lactate_mmol_l >= 0),
  test_protocol text,
  stage_label text,
  workload_value numeric,
  workload_unit text,
  heart_rate_bpm integer check (heart_rate_bpm is null or heart_rate_bpm > 0),
  rpe numeric check (rpe is null or (rpe >= 0 and rpe <= 10)),
  timing text check (timing in ('pre_session', 'during_session', 'post_session', 'morning', 'other')),
  source text not null check (source in ('manual', 'csv_import', 'device_candidate')),
  source_provenance text,
  confidence text not null default 'user_reported'
    check (confidence in ('user_reported', 'imported', 'imported_uncertain', 'device_unverified')),
  notes text,
  raw_import_ref uuid references public.journal_imports(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_lactate_measurements_user_measured_at
  on public.lactate_measurements(user_id, measured_at desc);

alter table public.lactate_measurements enable row level security;
create policy lactate_measurements_self on public.lactate_measurements
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create table public.nutrition_checklist_daily (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  date date not null,
  checklist_kind text not null default 'daily_dozen_style',
  category text not null,
  completed_count numeric,
  target_count numeric,
  source text not null default 'manual' check (source in ('manual', 'csv_import')),
  source_provenance text,
  confidence text not null default 'user_reported'
    check (confidence in ('user_reported', 'imported', 'imported_uncertain')),
  notes text,
  raw_import_ref uuid references public.journal_imports(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, date, checklist_kind, category)
);

create index idx_nutrition_checklist_daily_user_date
  on public.nutrition_checklist_daily(user_id, date desc);

alter table public.nutrition_checklist_daily enable row level security;
create policy nutrition_checklist_daily_self on public.nutrition_checklist_daily
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
```

`nutrition_daily_log` from FS-020 remains the macro daily-total table.
FS-021 links to it by user/date in application logic rather than
duplicating macro columns.

## 5. Parser fixture expectations

Synthetic-only fixtures cover:

- manual lactate text
- lactate CSV row
- Daily Dozen-style CSV/checklist row
- macro timing row linked to a training day

Fixtures must not include private names, emails, IDs, tokens, or real
journal data.
