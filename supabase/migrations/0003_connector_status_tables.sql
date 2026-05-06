-- Connector status tables — minimal latest-snapshot envelope.
--
-- DO NOT APPLY BLINDLY. Additive only. Apply 0001_durable_account_storage.sql
-- and 0002_manual_imports.sql first. Run against a Supabase branch /
-- preview project before touching production. The Cloudflare Worker
-- expects these tables to exist before its `dataSource.source` field
-- flips from `'placeholder'` to `'supabase'`.
--
-- Purpose:
--   These are OWNER / CONTROL-CENTRE STATUS tables — they hold the five
--   connector payloads (work_status, coder_lanes, build_status, handoff,
--   terminal_summary) consumed by the MCP / app-dev-centre Cloudflare
--   Worker. They are NOT athlete private memory. They are NOT public
--   app / user data. They MUST NOT contain raw athlete health values,
--   OAuth tokens, env secrets, or per-user PII. The bridge writer
--   (`scripts/bridge-snapshot-lanes.sh` / planned upsert daemon) and
--   the owner-tap UI are the only writers; the Worker is the only
--   reader.
--
-- Safety model:
--   - The Supabase service-role key BYPASSES RLS. Enabling RLS on
--     these tables does not gate service-role reads. Real safety
--     comes from:
--       * SUPABASE_SERVICE_ROLE_KEY held only as a Cloudflare Worker
--         secret + locally in .dev.vars (gitignored).
--       * The Worker's strict route allowlist — `/api/work_status`,
--         `/api/coder_lanes`, `/api/build_status`, `/api/handoff`,
--         `/api/terminal_summary` — every other path returns 404.
--       * No arbitrary Supabase query path in the Worker. The
--         Supabase adapter only exposes hardcoded
--         `fetch<TableName>` helpers that target the connector_*
--         tables; there is no `query(sql)` surface.
--       * Worker routes admin-token-gate every connector read.
--   RLS is still enabled with no policies as a defence-in-depth
--   layer against a future caller swapping to an `anon` key by
--   mistake.
--
-- Schema source of truth:
--   - chat-app/src/server/types/connector.ts (TypeScript shapes
--     inside `payload`)
--   - docs/CONNECTOR_SUPABASE_SCHEMA.md (this file's companion)
--
-- Latest-snapshot envelope:
--   id            — primary key (single-row tables use id = 'current';
--                   the lanes table keys on lane_id; the
--                   terminal_summary table uses bigserial id +
--                   lane_id).
--   generated_at  — when the writer assembled the snapshot (writer
--                   sets this, NOT a default).
--   updated_at    — when the row was last upserted (default now()).
--   source        — who wrote the row ('bridge' / 'owner' / 'worker'
--                   / 'cli'). Helpful for debugging; not gating.
--   payload       — jsonb document matching the connector TS interface.

begin;

-- ---------- A. connector_work_status ----------
create table if not exists public.connector_work_status (
  id text primary key default 'current' check (id = 'current'),
  generated_at timestamptz not null,
  updated_at timestamptz not null default now(),
  source text not null default 'bridge',
  payload jsonb not null
);
comment on table public.connector_work_status is
  'Owner/control-centre WorkStatus payload — single-row envelope. NOT athlete private memory. NOT public app/user data.';
alter table public.connector_work_status enable row level security;

-- ---------- B. connector_coder_lanes ----------
-- One row per lane_id. lane_id is the fixed-key equivalent of
-- id = 'current'.
create table if not exists public.connector_coder_lanes (
  lane_id text primary key check (
    lane_id in ('claude', 'codex', 'claude_chat', 'chatgpt', 'cowork')
  ),
  generated_at timestamptz not null,
  updated_at timestamptz not null default now(),
  source text not null default 'bridge',
  payload jsonb not null
);
comment on table public.connector_coder_lanes is
  'Per-lane CoderLaneRow payloads written by the local tmux bridge. NOT athlete private memory.';
alter table public.connector_coder_lanes enable row level security;

-- ---------- C. connector_build_status ----------
create table if not exists public.connector_build_status (
  id text primary key default 'current' check (id = 'current'),
  generated_at timestamptz not null,
  updated_at timestamptz not null default now(),
  source text not null default 'owner',
  payload jsonb not null
);
comment on table public.connector_build_status is
  'Single-row BuildStatus payload (Android + iOS release rows). NOT athlete private memory.';
alter table public.connector_build_status enable row level security;

-- ---------- D. connector_handoff ----------
create table if not exists public.connector_handoff (
  id text primary key default 'current' check (id = 'current'),
  generated_at timestamptz not null,
  updated_at timestamptz not null default now(),
  source text not null default 'owner',
  payload jsonb not null
);
comment on table public.connector_handoff is
  'Single-row Handoff payload (manualSteps, doNotTouch, safeToBuild). Owner-only writes for safeToBuild=true. NOT athlete private memory.';
alter table public.connector_handoff enable row level security;

-- ---------- E. connector_terminal_summary ----------
-- Append-only event log. Cap to 50 rows total via a periodic delete
-- (see retention block at the end of this file).
create table if not exists public.connector_terminal_summary (
  id bigserial primary key,
  lane_id text not null check (
    lane_id in ('claude', 'codex', 'claude_chat', 'chatgpt', 'cowork')
  ),
  generated_at timestamptz not null,
  updated_at timestamptz not null default now(),
  source text not null default 'bridge',
  payload jsonb not null
);
comment on table public.connector_terminal_summary is
  'Append-only TerminalSummaryEntry log. Cap 50 rows via retention sweep. NOT athlete private memory.';
create index if not exists connector_terminal_summary_lane_recent
  on public.connector_terminal_summary (lane_id, generated_at desc);
alter table public.connector_terminal_summary enable row level security;

commit;

-- ---------- Retention sweep (optional; run via pg_cron or manual) ----------
-- pg_cron is not enabled by default. Until it is, the bridge writer
-- can run this delete after each insert; alternatively, attach to
-- a Supabase scheduled task. Trims to the most recent 50 rows.
--
-- delete from public.connector_terminal_summary
-- where id not in (
--   select id from public.connector_terminal_summary
--   order by generated_at desc
--   limit 50
-- );
