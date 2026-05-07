-- FS-020 B-20a: journal imports, term normalization, and daily macro logs.
-- Additive only. Does not modify FS-018 tables from 0005.

create table if not exists public.journal_term_normalizations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  raw_text text not null,
  canonical_term text not null,
  category text not null check (
    category in (
      'medication',
      'peptide',
      'supplement',
      'nasal_spray',
      'inhaler',
      'sleep_aid',
      'caffeine',
      'nutrition_change',
      'training_change',
      'injury',
      'pain',
      'illness',
      'respiratory_treatment',
      'weight_cut_intervention',
      'surgery',
      'custom'
    )
  ),
  aliases text[] not null default array[]::text[],
  user_confirmed boolean not null default false,
  needs_user_confirmation boolean not null default true,
  confidence text not null default 'low' check (confidence in ('low', 'medium', 'high')),
  source text not null default 'user' check (source in ('user', 'imported_paste', 'imported_file', 'shared_dictionary')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, raw_text)
);

create index if not exists idx_journal_term_normalizations_user_raw_text
  on public.journal_term_normalizations(user_id, raw_text);

alter table public.journal_term_normalizations enable row level security;

drop policy if exists journal_term_normalizations_self on public.journal_term_normalizations;
create policy journal_term_normalizations_self on public.journal_term_normalizations
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create table if not exists public.journal_imports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  source_kind text not null check (
    source_kind in ('paste', 'csv_file', 'apple_notes', 'whoop_export', 'cronometer_export', 'other_file')
  ),
  source_filename text,
  raw_size_bytes integer not null check (raw_size_bytes >= 0),
  raw_hash text not null,
  parsed_count integer not null default 0 check (parsed_count >= 0),
  imported_count integer not null default 0 check (imported_count >= 0),
  skipped_count integer not null default 0 check (skipped_count >= 0),
  notes text,
  status text not null default 'preview' check (status in ('preview', 'applied', 'partial', 'cancelled')),
  created_at timestamptz not null default now(),
  applied_at timestamptz
);

alter table public.journal_imports enable row level security;

drop policy if exists journal_imports_self on public.journal_imports;
create policy journal_imports_self on public.journal_imports
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create table if not exists public.nutrition_daily_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  date date not null,
  protein_g numeric,
  carbs_g numeric,
  fat_g numeric,
  fiber_g numeric,
  calories integer,
  bodyweight_kg numeric,
  source text not null check (
    source in ('manual', 'imported_csv', 'imported_paste', 'cronometer_via_hub', 'apple_health', 'health_connect')
  ),
  source_provenance text,
  notes text,
  raw_import_ref uuid references public.journal_imports(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, date, source)
);

create index if not exists idx_nutrition_daily_log_user_date
  on public.nutrition_daily_log(user_id, date);

alter table public.nutrition_daily_log enable row level security;

drop policy if exists nutrition_daily_log_self on public.nutrition_daily_log;
create policy nutrition_daily_log_self on public.nutrition_daily_log
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
