-- Durable account-storage additive migration.
--
-- DO NOT APPLY BLINDLY. Review, dry-run against a branch/preview project
-- first, then apply with `npx supabase db push` or via the dashboard SQL
-- editor. This migration is additive only — it creates new tables + RLS
-- policies without touching any existing data.
--
-- Layering (mirrors docs/architecture/raw_source_layer + private_athlete_memory):
--   1. raw_source_events          — evidence layer, append/upsert safe
--   2. normalized_daily_metrics   — deterministic per-day roll-up
--   3. interpreted_daily_artifacts / interpreted_weekly_artifacts — AI read cache
--   4. athlete_memory             — slow-moving stable memory, versioned
--   5. memory_promotion_candidates — reviewable candidates only
--   6. source_connection_state    — per-source health + missingness
--   7. athlete_profiles           — minimal per-user scope anchor
--
-- Every user-data table enables RLS and scopes rows by auth.uid() so
-- no user can read or write another user's rows. Writes should go
-- through a trusted backend with the service role for the derived
-- layers; raw_source_events + user-owned HIIT/training logs may be
-- written by the authenticated mobile client when the write targets
-- a row owned by auth.uid() itself.

begin;

-- Ensure pgcrypto for gen_random_uuid() across tables.
create extension if not exists pgcrypto;

-- ---------- A. athlete_profiles ----------
create table if not exists public.athlete_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  display_name text,
  timezone text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.athlete_profiles enable row level security;
create policy "athlete_profiles_select_own" on public.athlete_profiles
  for select using (auth.uid() = user_id);
create policy "athlete_profiles_upsert_own" on public.athlete_profiles
  for insert with check (auth.uid() = user_id);
create policy "athlete_profiles_update_own" on public.athlete_profiles
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ---------- B. source_connection_state ----------
create table if not exists public.source_connection_state (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  source text not null check (source in ('whoop','apple_health','health_connect','cronometer','polar','samsung','manual','hiit','grappling_session')),
  status text not null check (status in ('connected','stale','missing_permission','auth_required','partial','error','not_connected')),
  last_ingested_at timestamptz,
  last_success_at timestamptz,
  last_failure_at timestamptz,
  last_failure_reason text,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  unique (user_id, source)
);
create index if not exists source_connection_state_user on public.source_connection_state(user_id);
alter table public.source_connection_state enable row level security;
create policy "scs_select_own" on public.source_connection_state
  for select using (auth.uid() = user_id);

-- ---------- C. raw_source_events ----------
create table if not exists public.raw_source_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  source text not null,
  source_record_id text not null,
  source_record_type text not null,
  local_date date,
  started_at timestamptz,
  ended_at timestamptz,
  payload jsonb not null,
  payload_hash text not null,
  ingested_at timestamptz not null default now(),
  provenance jsonb not null default '{}'::jsonb,
  unique (user_id, source, source_record_id, source_record_type)
);
create index if not exists raw_source_events_user_date on public.raw_source_events(user_id, local_date);
create index if not exists raw_source_events_user_source on public.raw_source_events(user_id, source);
alter table public.raw_source_events enable row level security;
create policy "rse_select_own" on public.raw_source_events
  for select using (auth.uid() = user_id);
create policy "rse_insert_own" on public.raw_source_events
  for insert with check (auth.uid() = user_id);

-- ---------- D. normalized_daily_metrics ----------
create table if not exists public.normalized_daily_metrics (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  local_date date not null,
  timezone text,
  recovery_score numeric,
  hrv_ms numeric,
  rhr_bpm numeric,
  sleep_hours numeric,
  sleep_performance_pct numeric,
  day_strain numeric,
  active_kcal numeric,
  workout_count int,
  hiit_minutes numeric,
  grappling_minutes numeric,
  source_coverage jsonb not null default '{}'::jsonb,
  missing_fields jsonb not null default '[]'::jsonb,
  computed_from_hash text,
  computed_at timestamptz not null default now(),
  unique (user_id, local_date)
);
create index if not exists ndm_user_date on public.normalized_daily_metrics(user_id, local_date desc);
alter table public.normalized_daily_metrics enable row level security;
create policy "ndm_select_own" on public.normalized_daily_metrics
  for select using (auth.uid() = user_id);

-- ---------- E. interpreted_daily_artifacts ----------
create table if not exists public.interpreted_daily_artifacts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  local_date date not null,
  artifact_version text not null,
  mode text not null check (mode in ('seed','partial','enriched')),
  summary jsonb not null,
  flags jsonb not null default '[]'::jsonb,
  recommendations jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  missingness jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (user_id, local_date, artifact_version)
);
create index if not exists ida_user_date on public.interpreted_daily_artifacts(user_id, local_date desc);
alter table public.interpreted_daily_artifacts enable row level security;
create policy "ida_select_own" on public.interpreted_daily_artifacts
  for select using (auth.uid() = user_id);

-- ---------- F. interpreted_weekly_artifacts ----------
create table if not exists public.interpreted_weekly_artifacts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  week_start date not null,
  week_end date not null,
  artifact_version text not null,
  mode text not null check (mode in ('seed','partial','enriched')),
  summary jsonb not null,
  trends jsonb not null default '{}'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  promotion_candidates jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  unique (user_id, week_start, artifact_version)
);
create index if not exists iwa_user_week on public.interpreted_weekly_artifacts(user_id, week_start desc);
alter table public.interpreted_weekly_artifacts enable row level security;
create policy "iwa_select_own" on public.interpreted_weekly_artifacts
  for select using (auth.uid() = user_id);

-- ---------- G. athlete_memory ----------
create table if not exists public.athlete_memory (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  memory_type text not null check (memory_type in ('baseline','preference','injury_context','training_pattern','recovery_pattern','schedule_context','nutrition_context')),
  key text not null,
  value jsonb not null,
  confidence numeric,
  source_artifact_ids jsonb not null default '[]'::jsonb,
  status text not null default 'active' check (status in ('active','superseded','rejected')),
  version int not null default 1,
  promoted_by text,
  promoted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists am_user_type on public.athlete_memory(user_id, memory_type, status);
create unique index if not exists am_user_type_key_active_version on public.athlete_memory(user_id, memory_type, key, version) where status = 'active';
alter table public.athlete_memory enable row level security;
-- Daily refresh MUST NOT mutate this table. Select-only for clients;
-- promotion writes go through a service-role backend path.
create policy "am_select_own" on public.athlete_memory
  for select using (auth.uid() = user_id);

-- ---------- H. memory_promotion_candidates ----------
create table if not exists public.memory_promotion_candidates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  candidate_type text not null,
  proposed_key text not null,
  proposed_value jsonb not null,
  rationale text,
  evidence_refs jsonb not null default '[]'::jsonb,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by text
);
create index if not exists mpc_user_status on public.memory_promotion_candidates(user_id, status);
alter table public.memory_promotion_candidates enable row level security;
create policy "mpc_select_own" on public.memory_promotion_candidates
  for select using (auth.uid() = user_id);
create policy "mpc_update_own" on public.memory_promotion_candidates
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

commit;

-- Notes:
-- - Writes to normalized_daily_metrics, interpreted_*_artifacts, and
--   athlete_memory are intentionally NOT exposed to the authenticated
--   client — they should be produced by a trusted backend using the
--   service role. RLS here is select-own to enforce read isolation.
-- - raw_source_events is insert-own so the mobile client can write its
--   own HIIT/training events directly under the user's auth scope.
--   Backend ingest paths can bypass RLS with the service role as
--   needed for aggregate jobs.
-- - memory_promotion_candidates allows the user to approve/reject
--   their own candidates without needing backend intervention. Actual
--   promotion INTO athlete_memory is still service-role gated.
