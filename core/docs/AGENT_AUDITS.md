# Agent audits — historical recovered suggestions

Where the audit output from prior agent runs (ChatGPT custom GPTs,
Codex audit prompts, Claude Code code-review subagents, etc.)
lives in the repo as a paper trail. This file is **historical /
informational only**. It does NOT drive active work — that flows
through `docs/FEEDBACK_SUGGESTIONS.md` after Aaron's approval.

Companion to:
- `docs/FEEDBACK_SUGGESTIONS.md` — candidate suggestions awaiting
  Aaron's approval before becoming active work.
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` — three-lane risk model
  for what suggestions can move through autonomously.
- `docs/APP_DEVELOPMENTS.md` — active priority order.
- `docs/CONTROL_CENTRE_MVP_SPEC.md` — iPhone Admin/Dev surface
  the suggestions feed into.

Updated 2026-05-07.

## Read-me-first

1. Items in this doc are **frozen historical text** from the
   audit that produced them. Source labels (e.g. `SUG-008`) are
   preserved verbatim where the audit provided them. If a
   different agent run later produces an item with the same
   number, it goes under a new section header — never overwrite.
2. The "Foundation done" section below pre-flags items that the
   audit asked for which have ALREADY landed. Each carries a
   commit SHA pointer. **Do not treat these as active work.**
3. Anything not in "Foundation done" stays a candidate until
   Aaron promotes it. Promotion happens in
   `docs/FEEDBACK_SUGGESTIONS.md`, never here.
4. Aaron approval is required before any candidate becomes
   active work AND before any completed item is removed from
   the backlog. This is the same rule pinned at the top of
   `docs/FEEDBACK_SUGGESTIONS.md`.

## Foundation done — items the audit asked for that have already shipped

Each of these was an audit suggestion BEFORE the work landed. They
are now infrastructure facts. Do NOT re-open them as active
suggestions. Aaron approval is required if any of them needs to
be reverted.

| Source ID | Audit ask | Landed | Pointer |
|---|---|---|---|
| SUG-008 | Create Supabase connector tables | DONE | `supabase/migrations/0003_connector_status_tables.sql`, applied via dashboard. Five tables: `connector_work_status`, `connector_coder_lanes`, `connector_build_status`, `connector_handoff`, `connector_terminal_summary`. |
| SUG-009 | Local tmux bridge producer (read-only, sanitised) | DONE | `scripts/bridge-snapshot-lanes.sh`, commit `fdf38eb` (initial), extended in `ff6d3ef` to emit terminal_summary + handoff, extended in `3030b47` to upsert to Supabase when env present. |
| (no ID) | Set Cloudflare Worker secrets so the Worker reads Supabase | DONE | `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` set via `wrangler secret put` (commit context `66c9594`); `/supabase/health` reports `configured: true, ping.ok: true`. |
| (no ID) | `/api/coder_lanes` returns real bridge data, not placeholder | DONE | Live since version `7a0ddf6c-9d77-4d70-9852-88dc0c1a2815`; `dataSource.source = supabase`, returns claude + codex rows with status enums. |
| (no ID) | `/api/terminal_summary` returns real terminal entries | DONE | Live; `dataSource.source = supabase`, returns up to 50 entries from `connector_terminal_summary` ordered `generated_at desc`. |
| (no ID) | Replace Railway dependency with Cloudflare + Supabase as active path | DONE | Railway is deprecated. Worker at `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/` is the active surface. See `docs/CLOUDFLARE_MIGRATION.md` and `docs/RAILWAY_CONNECTOR_TOOLS.md` (deprecation banner). |

If a future audit re-asks any of the above, the response is "done,
see commit pointer here" — not a new candidate.

## Recovered audit suggestions — pending intake

The audit body that the most recent prompt referred to (`[paste
Agent output]`) was NOT included in the message. This section
holds a placeholder until the actual audit text arrives.

When Aaron pastes the audit body:

1. The recovered text lands here under a new dated subsection
   (e.g. `### 2026-05-07 ChatGPT MCP audit — recovered text`),
   verbatim, with original source labels preserved.
2. Each item gets a one-line status flag: `foundation-done`,
   `candidate`, or `superseded` (with a pointer to the
   replacing item).
3. Candidate items get a corresponding entry in
   `docs/FEEDBACK_SUGGESTIONS.md` with `status: candidate`
   awaiting Aaron approval.
4. No item moves to active work without an explicit Aaron
   approval line in `docs/FEEDBACK_SUGGESTIONS.md`.

### 2026-05-07 — placeholder for unsourced corrections

The same prompt that asked for ingestion also pre-corrected the
six "foundation done" facts above. Those are the only items
acted on without the source body. Everything else waits for the
paste.

## Why this doc exists separately from `FEEDBACK_SUGGESTIONS.md`

- **Audit output is frozen.** It captures what the auditor
  thought at a moment in time. Editing it would erase the
  trail.
- **Suggestions evolve.** They get deduped, reframed, deferred,
  rejected, promoted. That mutation lives in
  `FEEDBACK_SUGGESTIONS.md`.
- **Auditors need the historical view too.** A future agent
  audit that asks "did we already consider X?" should read
  this file first.

## Anti-rules

- **Do not edit existing audit text.** Append new sections.
- **Do not promote suggestions from here directly.** They land
  as candidates in `FEEDBACK_SUGGESTIONS.md` first.
- **Do not mark anything done in this file.** "Done" is the
  job of the active backlog; this file only tracks the
  historical ask.
- **Do not paste tokens, secrets, or raw terminal logs into
  this file.** All audit text is sanitised by the same redactor
  the connector pipeline uses before landing here.
