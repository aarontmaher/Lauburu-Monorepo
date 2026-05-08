# Forever Improve lifecycle spec

The 8-state lifecycle every Forever Improve item travels
through. Pairs with `docs/APP_DEVELOPMENTS.md` § Permanent
improvement categories (the categories) + the action ledger
(rule 18) (the per-item record).

This is **doc only**. No app code. No EAS build.

## 0. Why a lifecycle

Forever Improve categories (mobile-only / gamification /
mastery / AI video / coaching / feedback incentives /
technique evolution etc.) span months. Without a state
machine, items drift between "vague idea" and "shipped"
without coordinator visibility — violating rule 18
(action ledger) and rule 14 (parallel priorities surfacing).

The lifecycle below replaces ad-hoc status strings ("in
progress" / "done" / "later") with a stable enum every coder
+ Aaron + Agent can reference.

## 1. The 8 states

```
   candidate ─► backlog ─► prioritized ─► in_progress ─► repo_ready
       │           │             │              │              │
       │           │             │              │              ▼
       │           │             │              │         awaiting_agent_qa
       │           │             │              │              │
       │           │             │              │              ▼
       │           │             │              │           verified
       │           │             │              │              │
       └───►   superseded   ◄────┴──────────────┴──────────────┘
                                  (any state may flip to superseded)
```

| State | Meaning | Required to enter | Visibility |
|---|---|---|---|
| `candidate` | Idea proposed (Aaron, coder, agent, user, AI). Not yet evaluated. | One-line summary + lane (which Forever Improve category). | Visible in Admin/Dev backlog; redacted summary on public MCP. |
| `backlog` | Aaron has reviewed + accepted as worth doing eventually. Not yet ranked. | Aaron approval (per rule 7's gate principle). | Same as candidate. |
| `prioritized` | Slotted into the Top 5 priorities or a defined sub-priority order. | Explicit position in `docs/APP_DEVELOPMENTS.md` Top-5 OR `connector_work_status.topPriorities` array. | Same. |
| `in_progress` | A coder (Claude/Codex/Agent) is actively executing. | Lane assigned; rule 12 cadence active (writeback per coder report). | Same; lane chip visible in Admin/Dev. |
| `repo_ready` | Implementation committed; tests pass; doc parity holds. | Commit SHA recorded; `npm run rules:test` + relevant contract tests PASS. | Same; release-gate chip shows pre-build state. |
| `awaiting_agent_qa` | Repo-ready; Agent functional audit pending per rule 4. | Commit SHA + audit playbook gate type recorded. | Same. |
| `verified` | Agent-confirmed per rule 5. Ready for `Aaron-approved for EAS build` if applicable. | Agent QA `status: pass` + `gate` matches the item's verification type. | Public-safe summary may surface count of verified items. |
| `superseded` | Replaced by another item, voided as obsolete, or rejected after evaluation. | Reason mandatory + `supersededBy` link if applicable. | Hidden from active backlog; preserved in audit. |

## 2. Lifecycle vs operating-rules four-status sequence (rule 8)

Rule 8 already defines the four-status sequence for FS-XXX
items: `Implementation-complete, awaiting Agent functional
confirmation` → `Agent-confirmed, ready for Aaron approval` →
`Aaron-approved for EAS build` → `Built/tester-ready`. The
8-state lifecycle does NOT replace it — it nests it:

| Lifecycle state | Maps to rule-8 status |
|---|---|
| `candidate` / `backlog` / `prioritized` | (pre-implementation; no rule-8 status yet) |
| `in_progress` | (active; transient) |
| `repo_ready` | `Implementation-complete, awaiting Agent functional confirmation` |
| `awaiting_agent_qa` | (in flight to confirmation) |
| `verified` | `Agent-confirmed, ready for Aaron approval` |
| (post-EAS build) | `Aaron-approved for EAS build` → `Built/tester-ready` (per rule 8) |
| `superseded` | (any state may exit here) |

For non-EAS-build items (doc-only specs, rule additions, MCP
schema work) the lifecycle ends at `verified` — the rule-8
sequence's EAS-build extension doesn't apply.

## 3. Schema (action ledger extension)

Each Forever Improve item is an action ledger row (rule 18)
with these additional fields:

```ts
interface ForeverImproveItem extends ActionLedgerRow {
  category: 'mobile_only_admin' | 'gamification' | 'verified_mastery'
          | 'ai_video' | 'community_reputation' | 'coaching'
          | 'mobile_coaching' | 'feedback_incentives'
          | 'technique_evolution' | 'mcp_memory'
          | 'audit_automation' | 'push_approval'
          | 'ai_spend_reduction' | 'deep_research_offload'
          | 'forever_improve_lifecycle' | 'other';
  lifecycleState: 'candidate' | 'backlog' | 'prioritized'
                | 'in_progress' | 'repo_ready' | 'awaiting_agent_qa'
                | 'verified' | 'superseded';
  proposedBy: 'aaron' | 'claude' | 'codex' | 'agent' | 'user' | 'ai';
  oneLineSummary: string;            // ≤140 chars
  category_quality_bar: string;      // which Forever Improve quality bar this serves
  fsCandidate: string | null;        // FS-XXX id once promoted
  commitShas: string[];              // commits that landed this item
  agentQaGate: string | null;        // gate type from INSTALLED_DEVICE_AUDIT_PLAYBOOK
  supersededBy: string | null;       // id of replacing item if superseded
  rejectionReason: string | null;
  createdAt: string;
  lifecycleHistory: Array<{ state: string; by: string; at: string; reason?: string }>;
}
```

State transitions are append-only ledger rows; nothing is
deleted or amended in place.

## 4. State transition rules

| From | To | Who can transition | Required evidence |
|---|---|---|---|
| `candidate` → `backlog` | Aaron | Confirmation that the idea fits a Forever Improve category + isn't a duplicate. |
| `backlog` → `prioritized` | Aaron | Position in Top-5 OR sub-priority list set. |
| `prioritized` → `in_progress` | Aaron OR coder claim | Lane assigned (Claude / Codex / Agent). |
| `in_progress` → `repo_ready` | Coder | Commit SHA + tests pass + doc parity. |
| `repo_ready` → `awaiting_agent_qa` | Coder | Audit gate type identified per `INSTALLED_DEVICE_AUDIT_PLAYBOOK.md`. |
| `awaiting_agent_qa` → `verified` | Agent | AGENT_QA `status: pass` recorded. |
| `awaiting_agent_qa` → `repo_ready` | Agent | If `status: fail`, kicks back for fix-up (rule 6). |
| any → `superseded` | Aaron OR coder with reason | Reason text + `supersededBy` link if replaced. |

Per rule 6 (`agent-not-confirmed = investigate`): a fail
result kicks the item back; coder + Aaron decide whether to
fix forward (back to `in_progress`) or supersede.

## 5. Surfacing in MCP

Public-safe: counts only by state.

```ts
{ count_by_lifecycle_state: { candidate: 12, backlog: 8, prioritized: 5, in_progress: 3, repo_ready: 2, awaiting_agent_qa: 1, verified: 47, superseded: 19 } }
```

Admin-token surface: full per-item detail.

The `connector_work_status.topPriorities` array (already
shipped per the 2026-05-09 refresh) is the prioritized-state
slice. The full backlog lives in `connector_backlog_items`
or extends `connector_handoff.auditFindings` (TBD —
schema-design follow-up).

## 6. Anti-rules

- **No silent state drift.** Every transition writes a
  ledger row.
- **No skipping states.** Cannot jump `candidate` →
  `verified` without traversing intermediate states.
- **No deletion.** `superseded` is the exit for retired
  items; rows persist for audit.
- **No per-coder shortcuts.** Coders cannot flip to
  `verified` on Aaron's behalf even with admin token —
  Agent QA is the gate.
- **No untyped categories.** Every item has a Forever
  Improve category enum; no freeform.

## 7. Codex handoff prompt — implementation

```
PROMPT-ID: CODEX-FS-XXX-FOREVER-IMPROVE-LIFECYCLE-IMPL-01
TYPE: CODEX
LANE: Action ledger schema + admin-dev backlog UI

MCP-FIRST: call project.get_current_state.

Reference (read first):
- docs/FOREVER_IMPROVE_LIFECYCLE_SPEC.md (this doc).
- docs/APP_DEVELOPMENTS.md § Forever Improve.
- docs/HUMAN_APPROVAL_GATE_SPEC.md (rule 21 ledger schema
  this extends).

GOAL
Wire the Forever Improve lifecycle into the existing action
ledger:
- Supabase: extend connector_backlog_items (or create new
  forever_improve_items table) with lifecycleState,
  category, proposedBy, oneLineSummary, fsCandidate,
  commitShas, agentQaGate, supersededBy, rejectionReason,
  lifecycleHistory.
- Worker: new MCP tools project.list_forever_improve_items
  (admin) + project.update_forever_improve_state(itemId,
  toState, reason?) (admin or per-role gated).
- Mobile: admin-dev Forever Improve panel with per-state
  filter + state-history view.

ANTI-RULES
- No silent state drift; every transition writes a ledger
  row.
- No deletion; superseded is the only exit.
- No EAS build dispatched.
```

Approval-gated.

## 8. Cross-references

- `docs/APP_DEVELOPMENTS.md` § Permanent improvement
  categories — the categories whose items run through this
  lifecycle.
- `docs/OPERATING_RULES.md` § 4 (re-audit) / § 5 (Agent-
  confirmed) / § 6 (investigate) / § 8 (four-status) /
  § 18 (action ledger).
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 state
  machine for the items that ALSO need approval-gate
  push (subset of `awaiting_agent_qa` + `verified`
  transitions).
- `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` — gate types
  the `agentQaGate` field references.
