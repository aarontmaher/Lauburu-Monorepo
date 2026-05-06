-- Connector status tables.
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
--   Worker. They are NOT athlete private memory. They MUST NOT contain
--   raw athlete health values, OAuth tokens, env secrets, or per-user
--   PII. The bridge writer
--   (`scripts/bridge-snapshot-lanes.sh` / planned upsert daemon) and
--   the owner-tap UI are the only writers; the Worker is the only
--   reader.
--
-- Schema source of truth:
--   - chat-app/src/server/types/connector.ts (TypeScript shapes)
--   - docs/CONNECTOR_SUPABASE_SCHEMA.md (this file's companion)
--
-- Each row is a thin envelope:
--   id          — primary key (single-row tables use id = 'current'; the
--                 lanes/terminal_summary tables key on lane_id /
--                 bigserial respectively).
--   scope       — string scope so a future shared-state model can host
--                 multiple projects; defaults to 'default'.
--   payload     — jsonb document matching the connector TS interface.
--   source      — who wrote the row ('bridge' / 'owner' / 'worker' /
--                 'cli'). Helpful for debugging; not gating.
--   status      — denormalised status enum string for tables where the
--                 value is queryable (coder_lanes only).
--   created_at  — first insert timestamp.
--   updated_at  — last upsert timestamp; bridge runs touch this.
--
-- All tables enable RLS with NO policies. The Worker reads via the
-- service-role key (bypasses RLS); no per-user reader is intended.
-- This means a future client with only an `anon` JWT cannot read any
-- of these rows — by design.

begin;

-- ---------- A. connector_work_status ----------
create table if not exists public.connector_work_status (
  id text primary key default 'current' check (id = 'current'),
  scope text not null default 'default',
  payload jsonb not null,
  source text not null default 'bridge',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.connector_work_status is
  'Owner/control-centre WorkStatus payload — single-row envelope. NOT athlete private memory.';
alter table public.connector_work_status enable row level security;

-- ---------- B. connector_coder_lanes ----------
-- One row per lane_id. status column is denormalised from
-- payload->>'status' so latest-status reads can index without a json
-- expression index.
create table if not exists public.connector_coder_lanes (
  lane_id text primary key check (
    lane_id in ('claude', 'codex', 'claude_chat', 'chatgpt', 'cowork')
  ),
  scope text not null default 'default',
  status text not null default 'idle' check (
    status in ('idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done')
  ),
  payload jsonb not null,
  source text not null default 'bridge',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.connector_coder_lanes is
  'Per-lane CoderLaneRow payloads written by the local tmux bridge. NOT athlete private memory.';
create index if not exists connector_coder_lanes_status_updated
  on public.connector_coder_lanes (status, updated_at desc);
alter table public.connector_coder_lanes enable row level security;

-- ---------- C. connector_build_status ----------
create table if not exists public.connector_build_status (
  id text primary key default 'current' check (id = 'current'),
  scope text not null default 'default',
  payload jsonb not null,
  source text not null default 'owner',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.connector_build_status is
  'Single-row BuildStatus payload (Android + iOS release rows). NOT athlete private memory.';
alter table public.connector_build_status enable row level security;

-- ---------- D. connector_handoff ----------
create table if not exists public.connector_handoff (
  id text primary key default 'current' check (id = 'current'),
  scope text not null default 'default',
  payload jsonb not null,
  source text not null default 'owner',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
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
  scope text not null default 'default',
  payload jsonb not null,
  source text not null default 'bridge',
  created_at timestamptz not null default now()
);
comment on table public.connector_terminal_summary is
  'Append-only TerminalSummaryEntry log. Cap 50 rows via retention sweep. NOT athlete private memory.';
create index if not exists connector_terminal_summary_lane_recent
  on public.connector_terminal_summary (lane_id, created_at desc);
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
--   order by created_at desc
--   limit 50
-- );
