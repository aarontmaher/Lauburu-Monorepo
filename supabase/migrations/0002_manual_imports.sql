-- Manual imports + unsupported-field side-table.
--
-- DO NOT APPLY BLINDLY. Additive only. Apply 0001_durable_account_storage.sql
-- first, then this. Run against a Supabase branch/preview project before
-- touching production.
--
-- Purpose:
--   manual_imports             — one row per imported file (WHOOP CSV zip,
--                                Apple Health XML, Cronometer CSV, etc.).
--                                Dedupe key is (user_id, file_hash).
--   unsupported_manual_fields  — one row per (user_id, import, column_name)
--                                we couldn't map into normalized_daily_metrics.
--                                Lets the parser carry forward without losing
--                                data; future parser versions can promote
--                                rows out of this side-table.
--
-- RLS scoped per-user via auth.uid(). No service-role-only tables here:
-- the user is allowed to see + insert their own imports because the
-- mobile app writes them directly.

begin;

create extension if not exists pgcrypto;

-- ---------- manual_imports ----------
create table if not exists public.manual_imports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  source text not null check (source in (
    'whoop_csv', 'apple_health_xml', 'cronometer_csv', 'generic'
  )),
  filename text,
  file_hash text not null,
  imported_at timestamptz not null default now(),
  date_range_start date,
  date_range_end date,
  parser_version text,
  rows_total int,
  rows_ingested int,
  rows_skipped int,
  metadata jsonb not null default '{}'::jsonb,
  -- Idempotent re-imports: same file hash from same user is a no-op.
  unique (user_id, file_hash)
);
create index if not exists mi_user_imported_at on public.manual_imports(user_id, imported_at desc);
create index if not exists mi_user_source on public.manual_imports(user_id, source);
alter table public.manual_imports enable row level security;
create policy mi_select_own on public.manual_imports
  for select using (auth.uid() = user_id);
create policy mi_insert_own on public.manual_imports
  for insert with check (auth.uid() = user_id);

-- ---------- unsupported_manual_fields ----------
-- Side-table so the parser never has to silently discard a column.
-- Sample values are stored as a small JSON array (cap server-side to
-- ~10 representative values) so a future parser can decide whether a
-- column is worth promoting into normalized_daily_metrics.
create table if not exists public.unsupported_manual_fields (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  manual_import_id uuid not null references public.manual_imports(id) on delete cascade,
  source text not null,
  column_name text not null,
  sample_values jsonb not null default '[]'::jsonb,
  observed_at timestamptz not null default now()
);
create index if not exists umf_user_import on public.unsupported_manual_fields(user_id, manual_import_id);
create index if not exists umf_user_column on public.unsupported_manual_fields(user_id, source, column_name);
alter table public.unsupported_manual_fields enable row level security;
create policy umf_select_own on public.unsupported_manual_fields
  for select using (auth.uid() = user_id);
-- Inserts go through the trusted backend (service role) since the
-- parser determines unsupported columns; do not expose insert to
-- authenticated clients.

commit;

-- Notes:
-- - Apply order: 0001_durable_account_storage.sql → THEN this file.
-- - manual_imports.unique (user_id, file_hash) makes re-uploading the
--   same WHOOP zip a no-op at the database layer regardless of how
--   many times the mobile client retries.
-- - rows_ingested + rows_skipped lets the mobile import-success alert
--   surface a truthful count without re-querying the import job.
-- - parser_version lets us run a future re-parse pass against the
--   raw_source_events evidence layer without losing the original
--   import provenance.
