-- Control Centre tables — Phase 2 of docs/CONTROL_CENTRE_MVP_SPEC.md.
--
-- DO NOT APPLY BLINDLY. Additive only. Apply
-- 0001_durable_account_storage.sql, 0002_manual_imports.sql, and
-- 0003_connector_status_tables.sql first. Run against a Supabase
-- branch / preview project before touching production.
--
-- Purpose:
--   Two owner / control-centre tables that back the rich
--   manualSteps and topBacklog fields in
--   GET /api/control_centre. NOT athlete private memory. NOT
--   public app / user data. The Cloudflare Worker reads these
--   via the service-role key; the mobile app only sees the
--   redacted snapshot.
--
-- Safety model (cross-reference 0003):
--   - Service-role key bypasses RLS. Real safety comes from
--     Worker-only secret + strict route allowlist + connector-
--     table-only code paths + admin-token gate on the route.
--   - RLS is still enabled with no policies as defence-in-depth.
--   - No tokens, raw terminal logs, file paths, EAS / run IDs,
--     or other private fields are written to these tables — the
--     bridge / owner-tap writers MUST sanitise upstream.

begin;

-- ---------- A. connector_manual_steps ----------
create table if not exists public.connector_manual_steps (
  id uuid primary key default gen_random_uuid(),
  scope text not null default 'default',
  text text not null check (char_length(text) <= 200),
  category text not null check (
    category in ('supabase', 'cloudflare', 'eas', 'play_console',
                'app_store_connect', 'github', 'other')
  ),
  blocking boolean not null default false,
  approval_required boolean not null default false,
  approval text not null default 'pending' check (
    approval in ('pending', 'approved', 'completed', 'declined')
  ),
  source text not null default 'owner',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.connector_manual_steps is
  'Owner / control-centre manual steps. Rich shape with category + approval enum. NOT athlete private memory.';
create index if not exists connector_manual_steps_recent
  on public.connector_manual_steps (updated_at desc);
alter table public.connector_manual_steps enable row level security;

-- ---------- B. connector_backlog_items ----------
create table if not exists public.connector_backlog_items (
  id uuid primary key default gen_random_uuid(),
  scope text not null default 'default',
  title text not null check (char_length(title) <= 120),
  priority int not null check (priority between 1 and 11),
  status text not null check (
    status in ('live', 'repo-only', 'tester-build', 'blocked', 'done')
  ),
  type text not null check (
    type in ('bug', 'ux_issue', 'feature_idea', 'release_blocker',
            'health_data_issue', 'ai_coaching_idea',
            'monetisation_payment_idea', 'railway_backend_issue',
            'source_integration_issue')
  ),
  risk_level text not null check (risk_level in ('low', 'medium', 'high')),
  needs_build boolean not null default false,
  source text not null default 'owner',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.connector_backlog_items is
  'Owner / control-centre backlog. Top-1 surface in /api/control_centre + suggestionCounts derivation. NOT athlete private memory.';
create index if not exists connector_backlog_items_open_priority
  on public.connector_backlog_items (priority asc, updated_at desc)
  where status != 'done';
alter table public.connector_backlog_items enable row level security;

commit;
