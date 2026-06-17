-- Custom timeline journal + metric-effect windows (FS-018).
--
-- DO NOT APPLY BLINDLY. Additive only. Apply 0001 through 0004 first.
-- Run against a Supabase branch / preview project before production.
--
-- Purpose:
--   journal_items          — one row per tracked custom item per user.
--   journal_events         — immutable start / stop / dose-change / note events.
--   journal_dose_periods   — computed materialized view of active periods.
--   metric_effect_windows  — computed association windows, never causation.
--
-- Safety:
--   User data is private. Tables use RLS scoped by auth.uid() = user_id.
--   Journal item/event names, doses, notes, and windows must never appear
--   in public MCP / no-auth tools. Control-centre may expose counts only.

begin;

create extension if not exists pgcrypto;

-- ---------- journal_items ----------
create table if not exists public.journal_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  category text not null,
  name text not null,
  unit text,
  default_dose numeric,
  default_frequency text,
  may_affect_metrics boolean not null default true,
  notes text,
  source text,
  confidence text not null default 'user_reported',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_journal_items_user_updated
  on public.journal_items(user_id, updated_at desc);
create index if not exists idx_journal_items_user_category
  on public.journal_items(user_id, category);
alter table public.journal_items enable row level security;
drop policy if exists journal_items_self on public.journal_items;
create policy journal_items_self on public.journal_items
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
comment on table public.journal_items is
  'Per-user custom timeline journal items. Private athlete context; never exported via no-auth MCP.';

-- ---------- journal_events ----------
create table if not exists public.journal_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id uuid not null references public.journal_items(id) on delete cascade,
  event_type text not null,
  effective_at timestamptz not null,
  dose numeric,
  unit text,
  frequency text,
  notes text,
  source text,
  confidence text not null default 'user_reported',
  created_at timestamptz not null default now()
);

create index if not exists idx_journal_events_item_effective
  on public.journal_events(item_id, effective_at);
create index if not exists idx_journal_events_user_effective
  on public.journal_events(user_id, effective_at desc);
alter table public.journal_events enable row level security;
drop policy if exists journal_events_self on public.journal_events;
create policy journal_events_self on public.journal_events
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
comment on table public.journal_events is
  'Per-user immutable custom journal events. Private athlete context; never exported via no-auth MCP.';

-- ---------- journal_dose_periods ----------
create materialized view if not exists public.journal_dose_periods as
select
  i.user_id,
  i.id as item_id,
  i.name,
  i.category,
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

create index if not exists idx_journal_dose_periods_user_period
  on public.journal_dose_periods(user_id, period_start desc);
create index if not exists idx_journal_dose_periods_item_period
  on public.journal_dose_periods(item_id, period_start desc);
revoke all on public.journal_dose_periods from anon, authenticated;
comment on materialized view public.journal_dose_periods is
  'Computed private journal dose periods. Refresh nightly / on demand. Not granted to anon/authenticated clients.';

-- ---------- metric_effect_windows ----------
create table if not exists public.metric_effect_windows (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id uuid not null references public.journal_items(id) on delete cascade,
  metric text not null,
  comparison_kind text not null,
  baseline_window_start timestamptz not null,
  baseline_window_end timestamptz not null,
  effect_window_start timestamptz not null,
  effect_window_end timestamptz not null,
  baseline_mean numeric,
  baseline_n int,
  effect_mean numeric,
  effect_n int,
  delta numeric,
  delta_pct numeric,
  confidence text not null,
  confounders text[],
  computed_at timestamptz not null default now()
);

create index if not exists idx_metric_effect_windows_user_computed
  on public.metric_effect_windows(user_id, computed_at desc);
create index if not exists idx_metric_effect_windows_item_metric
  on public.metric_effect_windows(item_id, metric, comparison_kind);
alter table public.metric_effect_windows enable row level security;
drop policy if exists metric_effect_windows_self on public.metric_effect_windows;
create policy metric_effect_windows_self on public.metric_effect_windows
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
comment on table public.metric_effect_windows is
  'Per-user computed association windows. No causation, no safety inference, no no-auth MCP export.';

commit;
