-- Connector overnight queue — durable backlog of long-running
-- autonomous tasks suitable for unattended overnight execution.
-- Schema mirrors `cloudflare-worker/src/overnight-queue.ts`
-- `OvernightQueueRow`. Test contract:
-- `cloudflare-worker/test/test-overnight-queue.ts`.
--
-- DO NOT APPLY BLINDLY. Apply 0001..0006 first. Run against a
-- Supabase branch / preview project before touching production.
-- The Cloudflare Worker `project.get_current_state` payload
-- gains an `overnightQueue` summary derived from these rows;
-- the admin tool `project.list_overnight_queue` returns the
-- redacted full rows.
--
-- Safety model:
--   - Same as 0003_connector_status_tables.sql: service-role
--     reads bypass RLS; safety comes from the worker's
--     hardcoded fetch helpers + admin-token gating on the
--     admin tool. RLS is still enabled with no policies as
--     defence in depth.
--   - Public MCP exposes count + recommendedTaskId +
--     safeToRunUnattended + hasStaleEntries only — never
--     row content.
--   - Admin tool returns `redactOvernightRowForAdmin` rows
--     (title truncated to 140 chars, dependencies replaced
--     with dependency_count, outcome_summary capped at 140).
--
-- Anti-rules baked into the schema:
--   - title is text NOT NULL with a CHECK ≤ 140 chars; matches
--     the validator in overnight-queue.ts.
--   - lane_owner is a CHECK against the four allowed values.
--   - interrupt_priority + suggested_execution_window have
--     CHECKs against the spec enums.
--   - progress_pct is constrained to [0, 100].
--   - dependencies is a uuid[] (Postgres array) — caller
--     validates referential integrity, the schema enforces
--     structural shape only.
--   - in-flight rows (started_at not null, completed_at null)
--     are never re-recommended; that contract lives in the
--     worker pickRecommendedTask helper, not as a schema check.

begin;

create table if not exists public.connector_overnight_queue (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) between 1 and 140),
  lane_owner text not null check (lane_owner in ('claude', 'codex', 'agent', 'aaron')),
  estimated_unattended_runtime_minutes integer not null check (estimated_unattended_runtime_minutes >= 0),
  requires_human_interaction boolean not null default false,
  safe_overnight boolean not null default false,
  dependencies uuid[] not null default '{}',
  interrupt_priority text not null check (
    interrupt_priority in ('p0', 'p1', 'p2', 'p3', 'overnight_only')
  ),
  repo_only_relevance boolean not null default false,
  preview_only_relevance boolean not null default false,
  installed_build_verified_relevance boolean not null default false,
  suggested_execution_window text not null check (
    suggested_execution_window in (
      'weeknight_us_pt',
      'weekend_us_pt',
      'any_idle',
      'business_hours_us_pt',
      'manual_only'
    )
  ),
  progress_pct numeric(5, 2) not null default 0 check (progress_pct between 0 and 100),
  outcome_summary text check (outcome_summary is null or char_length(outcome_summary) <= 500),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  -- Lifecycle ordering — completed implies started.
  check (completed_at is null or started_at is not null),
  check (started_at is null or started_at >= created_at),
  check (completed_at is null or completed_at >= started_at)
);

comment on table public.connector_overnight_queue is
  'Owner/control-centre overnight prompt queue. RECOMMENDATION ONLY — never auto-claimed. Public MCP exposes counts only; admin tool returns redacted rows. NOT athlete private memory. NOT public app/user data.';

-- Index for the worker''s recommendation query: priority asc,
-- created_at asc (FIFO within priority), filtered to rows that
-- have not started or completed.
create index if not exists connector_overnight_queue_active_priority
  on public.connector_overnight_queue (interrupt_priority, created_at asc)
  where completed_at is null and started_at is null;

-- Index for stale-age computation by updated_at desc — Admin/Dev
-- list view sorts on this.
create index if not exists connector_overnight_queue_updated_desc
  on public.connector_overnight_queue (updated_at desc);

-- Auto-bump updated_at on every UPDATE. The worker''s upsert
-- path also writes updated_at explicitly; this trigger covers
-- direct-SQL maintenance edits.
create or replace function public.connector_overnight_queue_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists connector_overnight_queue_touch on public.connector_overnight_queue;
create trigger connector_overnight_queue_touch
  before update on public.connector_overnight_queue
  for each row execute function public.connector_overnight_queue_touch_updated_at();

alter table public.connector_overnight_queue enable row level security;

commit;

-- ---------- Stale sweep (optional; pg_cron or manual) ----------
-- The worker computes stale_age_hours at read time; this sweep
-- is purely a hygiene action that auto-completes rows abandoned
-- after a long timeout. Leave commented until pg_cron is enabled.
--
-- update public.connector_overnight_queue
-- set completed_at = now(), outcome_summary = 'auto-completed: stale > 30 days'
-- where started_at is not null
--   and completed_at is null
--   and started_at < now() - interval '30 days';
