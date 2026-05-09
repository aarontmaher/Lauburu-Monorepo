# Queue taxonomy spec

Three durable queues plus the existing overnight queue, each
with a clear lane owner, a focused scope, and a shared
display contract. Pairs with `docs/MCP_MEMORY_ARCHITECTURE_SPEC.md`
(typed memory artifacts), `docs/FOREVER_IMPROVE_LIFECYCLE_SPEC.md`
(8-state lifecycle every queue item travels), and
`docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 (overnight queue
implementation Codex shipped in `7193ee1`).

This is **doc + helpers + tests only** this turn. Schema /
Admin/Dev UI implementation is staged for Codex per § 6.

## 0. Why three queues + overnight

The Forever Improve backlog (per `docs/APP_DEVELOPMENTS.md`
§ "Permanent improvement categories") spans 9 categories.
Without typed lanes, every item competes for the same
"Top 5 priorities" slot — and "phone-side admin polish"
ends up arguing with "FS-XXX feature shipping" over
the same priority queue.

The 3 queues separate concerns by **owner-lane** so each
coder knows what's theirs:

| Queue | Owner | Scope | Cross-rule |
|---|---|---|---|
| **Automation Workflow** | Claude | Mobile control via Admin/Dev tab. Push notification automation. No-idle routing. MCP freshness/writeback reliability. Approval-gated build/deploy workflows. Safe admin actions only; public/no-auth read-only. | rules 11 / 12 / 14 / 18 / 19 / 20 / 21 / 22 / 23 / 24 |
| **App Functionality** | Codex | Health source connectivity. Journal / FS-018 / FS-020. Training tab. Map. Coaching. Verified mastery. AI video analysis. Anything that ships as part of the mobile bundle's user-facing functionality. | rules 7 / 8 / 9 / 22 / 23 |
| **App UX/UI** | Agent | Visual polish. Premium UI primitives migration. Per-screen redesigns. Rule-9 anti-claim copy audits. Dark theme cohesion. Accessibility. | rules 9 / Forever Improve § AI video analysis (audit confidence ladder) |
| **Overnight prompt queue** | shared (any owner) | Long-running unattended tasks per `docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 — already shipped in Codex `7193ee1`. Items here optionally inherit a primary queue from the 4 above/below for routing. | rule 7 (no overnight EAS / Play / TestFlight without explicit approval) |
| **Audit / Review** | Agent (primary) + Claude/Codex (secondary) | Repo audits, recurring full-app screenshot audits, code review, agent-confirmed gate runs, FS-XXX functional confirmation, drift checks per Forever Improve. NOT the same as approval gates — these PRODUCE evidence; approval gates CONSUME it. | rules 1 / 4 / 5 / 6 + `INSTALLED_DEVICE_AUDIT_PLAYBOOK` |
| **Human Approval** | Aaron (consumer) + push surface (producer) | Pending approvals from any source — EAS build, Worker deploy, Supabase migration, AI spend, research export, public release, FS-XXX promotion, technique publishing. Surfaces in Admin/Dev approval centre + push notifications per rule 21. | rules 7 / 21 / 22 / 23 |

Queues do **NOT** override the Top-7 priority ordering or
P0/P1 assignments. They organise the **inside** of those
priorities so the right coder picks up the right item
without churn.

## 1. Automation Workflow Queue scope (Claude-owned)

Sub-items per Aaron's directive, in dependency order:

| # | Sub-item | Status today | Cross-ref |
|---|---|---|---|
| 1.1 | Mobile control through the Admin/Dev tab | LIVE | Codex `e51d179` + `9f3143a` + `634bb18` + Claude `49841b0` |
| 1.2 | Automation control through push notifications | PARTIAL — foundation tier | Codex `c6fb518` + `eb81060`; final all-idle wire pending `CODEX-FS-XXX-ALL-IDLE-PUSH-NOTIFICATION-01` |
| 1.3 | Worker / lane no-idle routing | LIVE | Codex `dd4f8c8` (rule 24) + `7193ee1` (overnight queue idle-lane recommendation) |
| 1.4 | MCP freshness / writeback reliability | LIVE | Claude `49841b0` (4-state staleReason union) + watcher daemon in `d6aa976` (race-attribution-misleading; inline header credits Claude) |
| 1.5 | Overnight autonomous prompt queue | LIVE | Codex `7193ee1` |
| 1.6 | Approval-gated build / deploy workflows | PARTIAL — spec'd; runtime gates pending | `docs/HUMAN_APPROVAL_GATE_SPEC.md` + `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md` |
| 1.7 | Safe admin actions only; public / no-auth read-only | LIVE | rule 22 privacy floor + connector sanitization rules |

Anti-rules for this queue:
- No EAS / Play / TestFlight upload.
- No Worker production deploy.
- No production release.
- No installed-device verified claim.
- Public / no-auth surfaces stay read-only.

## 2. Display contract (every queue + every item)

Every queue surface (Admin/Dev panel, MCP `project.list_queue_items`
admin tool, public-safe MCP summary) MUST surface these fields
per item:

| Field | Required | Note |
|---|---|---|
| `id` | yes | uuid |
| `title` | yes | ≤140 chars |
| `queue_kind` | yes | `automation_workflow` \| `app_functionality` \| `app_ux_ui` \| `overnight` |
| `lane_owner` | yes | `claude` \| `codex` \| `agent` \| `aaron` (matches queue_kind owner per § 0 table; `overnight` queue can have any) |
| `status` | yes | per the `FOREVER_IMPROVE_LIFECYCLE_SPEC` 8-state enum: candidate / backlog / prioritized / in_progress / repo_ready / awaiting_agent_qa / verified / superseded |
| `priority` | yes | `P0` \| `P1` \| `P2` \| `P3` \| `overnight_only` |
| `stale_age_hours` | yes | computed at read time per § 4 |
| `progress_pct` | yes | 0–100; 0 for non-started; 100 only when `status = verified` |
| `next_prompt_target` | yes | `{ owner, prompt_id_or_title, approval_required: bool }` |
| `human_action_required` | yes | boolean — `true` when the item is blocked on Aaron approval / device retest / vendor console |
| `risk` | yes | `low` \| `medium` \| `high` \| `irreversible` — inherited from the underlying action's reversibility (see § 5 risk classification) |
| `dependencies` | optional | uuid[] referring to other queue items / action-ledger rows |
| `recurrence` | optional (audit queue only) | `{ cron: string, lastRunAt?: string, nextRunAt?: string }` for recurring full-app audits |
| `escalation_source` | optional (audit queue only) | `{ kind: 'bug' \| 'improvement' \| 'suggestion', source_user_id?: string, original_finding_id?: string }` for items escalated from user-feedback / agent audits |
| `approval_gate_id` | optional (human approval queue only) | uuid → `connector_action_ledger` row with `gateState: 'waiting_for_approval'` per rule 21 |

Public-safe surface MUST show `count` per `queue_kind` + per
`status` + per `priority` only. Full per-item rows are
admin-token gated (rule 22 privacy floor).

## 3. Classification rules

A new queue item is classified at insertion time by the helper
in `scripts/queue-taxonomy-helpers.mjs`. The classifier
returns the `queue_kind` + suggested `lane_owner` from the
item's title + (optionally) explicit lane hint.

Rule order (first match wins):

1. **Explicit lane hint**: if title contains `[automation]`,
   `[functionality]`, `[ux]`, `[overnight]`, `[audit]`, or
   `[approval]` tag, that wins — manual override.
2. **Human Approval keywords**: approve, approval, pending
   approval, awaiting aaron, EAS build approval, Worker
   deploy approval, public release, AI spend gate, research
   approval, technique publish (these surface in the rule
   21 push gate).
3. **Audit / Review keywords**: audit, review, recurring
   audit, drift check, screenshot audit, click-through,
   agent-confirm, FS-XXX functional confirmation, AGENT_QA,
   bug report, improvement, suggestion-escalation.
4. **Automation Workflow keywords**: MCP, freshness,
   writeback, watcher, push, gate (approval gates excluded —
   covered above), lane, idle, admin/dev, deploy, bridge,
   snapshot, audit-bundle, control-centre, no-idle,
   staleReason, heartbeat.
5. **App UX/UI keywords**: dark theme, premium, palette,
   primitive, copy, hedge, anti-claim, contrast, padding,
   layout, redesign, polish, accessibility, screen-record-only.
6. **App Functionality keywords**: journal, parser, health
   connect, apple health, training, map, syllabus, drill,
   technique, mastery, video analysis, coach, FS-018, FS-020,
   FS-021, FS-022.
7. **Overnight keywords**: overnight, unattended, long-
   running, batch, 8-hour-build, cron.
8. **Default fallback**: `automation_workflow` (Claude's
   default), with an `unclassified: true` flag so reviewers
   re-classify.

Order matters: Human Approval keywords win over Automation
keywords (an "EAS build approval" item belongs to the
approval queue, not the automation queue). Audit keywords
win over functionality keywords (a "FS-020 audit" is an
audit-queue item, not a functionality-queue item).

## 4. Stale age + progress contract

`stale_age_hours = (now - max(updated_at, last_status_change_at)) / 3600`

Stale thresholds (item flips to `stale` indicator):
- `automation_workflow`: 72h.
- `app_functionality`: 168h (7d).
- `app_ux_ui`: 168h (7d).
- `overnight`: 24h (overnight items rarely sit; a stale
  overnight item is a workflow bug).
- `audit`: 168h (7d). Recurring audits with `recurrence`
  field flip to stale at `nextRunAt` rather than the
  generic threshold.
- `human_approval`: 96h (4d) — Aaron-action items get a
  shorter staleness window because every day of delay
  means an undecided gate. After staleness, the gate
  auto-`expired` per rule 21 § 1 (after a 6d push warning,
  per HUMAN_APPROVAL_GATE_SPEC § 1).

Progress contract:
- `0` until `status === 'in_progress'`.
- `>0` only when there's a measurable artefact (commit SHA
  in `commitShas`, screenshot in `screenshotRefs`, etc.).
- `100` ONLY when `status === 'verified'` AND
  `agent_qa.status === 'pass'` for the relevant gate.

`status === 'superseded'` clears progress to `null` (not 0)
to distinguish "abandoned" from "not started".

## 4.5 Risk classification

Every item carries a `risk` field inherited from the
underlying action's reversibility. Used by Admin/Dev display
+ push payloads + recurring-audit cadence selection.

| Risk | Examples | Approval push wording bias |
|---|---|---|
| `low` | Doc edits / spec additions / read-only audits / classifier changes / bridge:snapshot | "Recommended; low risk." |
| `medium` | Worker preview deploy / npm dep bump / EAS Internal Testing build / non-destructive Supabase additive migration | "Approval recommended; reversible by re-deploy." |
| `high` | Worker production deploy / Play Internal upload / TestFlight Team release / DNS cutover | "Approval required; partial rollback path exists." |
| `irreversible` | Public App Store / Play Production release / destructive Supabase migration (DROP/TRUNCATE) / force-push to main / shared-secret rotation | "**Irreversible.** Approval required; explicit confirmation needed." |

Risk for the Human Approval queue is inherited from the
underlying action's class. Audit-queue items are typically
`low` (read-only) but may be `medium` if they include
destructive cleanup steps.

## 4.6 Recurring full-app audits

Audit-queue items may carry a `recurrence` cron schedule.
Default cadences for the standard audit gates per
`docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md`:

| Audit gate | Default cadence | Owner | Risk |
|---|---|---|---|
| `forever_improve_drift` (Gate C) | weekly (`0 4 * * MON`) | Agent | low |
| `pre_eas_sanity` (Gate F) | per build approval; not cron-scheduled | Agent | low |
| `admin_dev_proof_checklist` | quarterly (`0 4 1 1,4,7,10 *`) | Agent | low |
| `release_gate` (Gate A) | NEVER cron-scheduled — runs only when an installed-device gate is staged | Aaron + Agent | medium |
| `health_connect_crash_retest` (Gate D) | NEVER cron-scheduled — runs only post-build install | Aaron + Agent | medium |

Codex (or a Claude-shipped daemon, see § 6 alt-handoff)
schedules + dispatches the cron audits; the audit queue
records `lastRunAt` + `nextRunAt`. Recurring audits NEVER
override the P0/P1 protection (per § 5).

## 5. P0 / P1 protection

Queue items NEVER override Top-7 priorities. The
recommendation surface (per `7193ee1` idle-lane router
+ rule 24 no-idle dispatcher) does the priority arithmetic:

1. Active P0 blockers always win (currently: Health Connect
   installed-device gate, Worker stale-rules deploy, iOS
   Admin/Dev MCP-unavailable retest).
2. Active P1 work follows.
3. Queue items are recommended ONLY when no P0/P1 owns the
   idle lane.

When the **Health Connect installed-device gate** is BLOCKED
(today's state per `audit-2026-05-09T08:12-codex-hc-app-not-listed`),
NO queue item — even one tagged `P0` inside its queue —
overrides the HC gate's blocking status. The HC gate sits
ABOVE all queues until cleared by Aaron + v21 retest.

## 6. Codex handoff — schema + Admin/Dev UI implementation

This doc + helpers + tests are doc-only. Actual schema
extension + Admin/Dev panel + MCP tool live in a Codex
batch.

```
PROMPT-ID: CODEX-FS-XXX-QUEUE-TAXONOMY-IMPL-01
TYPE: CODEX
LANE: Supabase schema + Worker MCP tools + Admin/Dev panel
APPROVAL: rule 7 + rule 13 — Aaron explicit approval required.

GOAL
Wire the 3 named queues + the existing overnight queue per
docs/QUEUE_TAXONOMY_SPEC.md.

SCOPE PHASE 1
1. Supabase migration (additive): extend
   connector_overnight_queue (or rename to connector_queue_items)
   with queue_kind enum + the display-contract fields per
   § 2. Index on (queue_kind, status, priority).
2. Worker tool project.list_queue_items(queue_kind?, status?,
   lane_owner?) (admin scope) returns full rows.
   project.get_current_state.queues: { count_by_kind,
   count_by_status, count_by_priority, recommendedTaskId,
   safeToRunUnattended } (public-safe summary).
3. Worker tool project.classify_queue_item(title, hints?)
   uses scripts/queue-taxonomy-helpers.mjs at server-side
   (same TS classifier ported or imported).
4. Admin/Dev panel: 4 collapsible sub-sections (one per
   queue) reusing the existing Overnight Queue surface
   from 7193ee1 + the StatusPill primitive from 634bb18.
5. Tests: schema lock + classifier parity (TS + JS run the
   same fixtures); P0/P1 protection assertion.

ANTI-RULES
- No EAS / Play / TestFlight upload.
- No production release.
- No public exposure of full row content; counts only on
  public surfaces.
- No queue can override Top-7 priorities (P0 protection
  test required).
- HC installed-device gate stays P0 until cleared.

VERIFICATION
- Schema lock test PASS.
- Classifier parity (TS Worker + JS scripts agree on every
  fixture).
- P0 protection: simulate an active P0 blocker + a P0-tagged
  queue item; recommendation surface returns the BLOCKER, not
  the queue item.
- npm run rules:test PASS (24 rules).
- npm run mcp:test:public-redaction PASS.
```

Approval-gated.

## 7. Anti-rules (umbrella)

- **Queues NEVER override Top-7 priorities or P0 blockers.**
  HC installed-device gate stays P0 until cleared.
- **No EAS / Play / TestFlight upload from queue runs.**
- **No production release from queue.**
- **No silent queue mutation.** Every state transition writes
  to action ledger per rule 18.
- **No public exposure of full per-item content.** Counts +
  redacted titles only on public-safe surfaces.
- **No cross-lane sweeps.** Owner enforced at insert time;
  manual reclassification recorded as a transition.
- **No untyped queue.** Every item has an explicit
  `queue_kind` + `lane_owner` (no inferred-only).

## 8. Cross-references

- `docs/MCP_MEMORY_ARCHITECTURE_SPEC.md` — typed memory
  artifacts; queue items are a memory-artifact subtype.
- `docs/FOREVER_IMPROVE_LIFECYCLE_SPEC.md` — 8-state
  lifecycle queue items travel.
- `docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 — overnight queue
  Codex shipped in `7193ee1`; this spec extends it.
- `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md` — synthesis of
  approval push surfaces; Automation Workflow Queue items
  with `human_action_required: true` route through this.
- `docs/ADMIN_DEV_PROOF_CHECKLIST.md` § 7B — phone-first
  acceptance rows; queue display rows added there.
- `docs/APP_DEVELOPMENTS.md` § Top 7 priorities — queues
  organise WITHIN priorities, never replace them.
- `docs/OPERATING_RULES.md` § 7 / § 9 / § 11 / § 12 / § 14 /
  § 18 / § 19 / § 20 / § 21 / § 22 / § 23 / § 24.
