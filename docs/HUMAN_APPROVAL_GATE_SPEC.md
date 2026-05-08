# Human-approval push gate — spec (operating rule 21)

When automation pauses awaiting Aaron's approval, the app
notifies Aaron via push notification — even if the app is
closed — and surfaces an Approve / Defer / Block decision in
the Admin/Dev approval centre. Approved gates resume
automation from the exact next step in the action ledger.

This is **spec only**. No app code. No Worker code change.
No EAS build. Implementation is a Codex follow-up batch
gated on Aaron approval (per rule 7 + rule 13).

## 0. Relationship to existing rules

| Rule | Relationship |
|---|---|
| Rule 7 (EAS build cost control) | Rule 21 enforces the explicit-Aaron-approval clause in rule 7 by giving it a notification + state-machine surface. EAS-build-approval is one specific instance of an approval gate. |
| Rule 11 (MCP-first) | Approval-gate writes go through MCP / action ledger. Reads honour MCP-first; the push payload includes a freshness check. |
| Rule 18 (action ledger) | The action ledger is the canonical store for `waiting_for_approval` rows. State transitions are recorded as ledger updates. |
| Rule 20 (all-idle notification) | Reuses the same push wiring (`expo-notifications`, admin-only / email-allowlisted). Rule 21 is the second push surface that lands on top of rule 20's plumbing. |
| Rule 13 (clear-steps automate-first) | Approval gates ARE the "manual Aaron step" section of every output where rule 13's three-section split applies. |

## 1. Approval gate state machine

```
              ┌───────────────────────┐
              │ waiting_for_approval  │
              └──┬──────┬──────┬──────┘
                 │      │      │
       ┌─────────┘      │      └─────────┐
       │                │                │
       ▼                ▼                ▼
   approved          deferred          blocked
       │                │                │
       │                │                │
   resume         re-fire after     close gate;
  automation     deferred_until     follow-up
                                   prompt required
                 ┌──────────────┐
                 │   expired    │ ──► (auto-transition
                 └──────────────┘     to `blocked` with
                                       reason
                                       `expired_no_response`)
```

| State | Meaning | Next action |
|---|---|---|
| `waiting_for_approval` | Automation paused; Aaron has not yet responded. | Push notification sent. Gate visible in Admin/Dev approval centre. |
| `approved` | Aaron tapped Approve (push action button OR in-app). | Automation resumes from the action ledger row's `nextStep` field. |
| `deferred` | Aaron tapped Defer (with optional duration: 1h / 24h / "until I say"). | Gate re-fires push after `deferred_until` timestamp. Default duration 24h. |
| `expired` | No response within configured TTL (default: 7 days). | Auto-transitions to `blocked` with `expired_no_response`. Logged but not pushed. |
| `blocked` | Aaron tapped Block, OR `expired` auto-transitioned, OR a coder marked the gate `blocked` after diagnosis. | Gate is closed. A new Codex/Claude prompt must be issued to advance — automation does NOT silently resume. |

State transitions are recorded as ledger updates with
`updatedAt`, `actorId` (Aaron / Claude / Codex / agent), and
`reason` field.

## 2. Action ledger schema (extension to rule 18)

The action ledger already has `status: pending | active |
completed | blocked | void | superseded` (rule 18). For
approval gates we add fields without changing the existing
status enum:

```ts
interface ApprovalGate {
  // existing rule-18 fields (id, owner, lane, etc.)
  id: string;
  owner: 'aaron';
  targetWorkerOrPerson: 'aaron';
  lane: 'approval_gate';
  actionText: string;
  status: 'pending';                  // ledger-level rule-18 status

  // NEW gate-level state
  gateState: 'waiting_for_approval' | 'approved' | 'deferred' | 'expired' | 'blocked';
  whatNeedsApproval: string;          // ≤140 chars
  whyItMatters: string;               // ≤280 chars; consequence summary
  topPriorityContext: string;         // pulled from project.get_current_state.priority.title
  safeDefault: string;                // e.g. "Defer 24h" / "No build"
  deferredUntil?: string;             // ISO timestamp, set when gateState = 'deferred'
  expiresAt: string;                  // ISO timestamp, default now + 7d
  approvedAt?: string;
  blockedReason?: string;             // 'aaron_blocked' | 'expired_no_response' | 'coder_diagnosed'
  followUpPromptId?: string;          // set when blocked; references the next prompt to dispatch
  pushHistory: Array<{ sentAt: string; channel: 'expo_push' | 'in_app_banner'; deliveryStatus?: string }>;
  approvalEvidence?: { approvedBy: 'aaron'; approvedAt: string; method: 'push_action' | 'admin_dev_centre' | 'mcp_tool_call' };
}
```

Public MCP surfaces show compact redacted summaries
(`gateState`, `whatNeedsApproval` truncated to ≤80 chars,
`expiresAt`); full detail is admin-token-gated.

## 3. Push notification UX

### 3.1 Trigger

A push fires when an action ledger row transitions into
`gateState: 'waiting_for_approval'`, OR re-fires when a
`deferred` gate's `deferredUntil` elapses.

Push permissions must be granted (per rule 20's wiring).
If permissions are denied, the gate stays visible in the
in-app Admin/Dev approval centre but no push goes out.

### 3.2 Payload

```ts
{
  title: `Approval needed: ${whatNeedsApproval}`,
  body: `${whyItMatters} · Top priority: ${topPriorityContext} · Safe default: ${safeDefault}`,
  data: {
    gateId: string,
    gateState: 'waiting_for_approval',
    expiresAt: string,
    deepLink: 'lauburu://admin-dev/approval-centre/<gateId>',
    freshnessSnapshot: { isFresh: boolean, source: 'mcp' | 'fallback', generatedAt: string },
  },
  actions: [          // platform-dependent; iOS notification categories / Android notification actions
    { id: 'approve', title: 'Approve' },
    { id: 'defer_24h', title: 'Defer 24h' },
    { id: 'block',   title: 'Block' },
  ],
}
```

Where the platform does not support inline action buttons
(some Android OEM customisations strip them), the fallback
is tap-to-open the Admin/Dev approval centre filtered to
`gateId`.

### 3.3 Throttling + dedupe

- One push per gate per state-transition. No re-firing on the
  same `waiting_for_approval` state until 15 minutes elapse
  (matches rule 20's throttle).
- `deferred` re-fire respects the user's `deferred_until`
  exactly; no early re-fire.
- If multiple gates are waiting, group into a single
  digest push every 30 minutes after the first fires
  individually — body becomes "3 approvals waiting" with the
  highest-priority gate's `whatNeedsApproval` quoted.

### 3.4 Privacy

- Payload MUST NOT include raw terminal text, journal data,
  PII, or admin tokens. The redaction surface in
  `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
  applies.
- `deepLink` must NOT include sensitive tokens; the gate is
  re-fetched from the Worker after the deep-link opens, with
  the user's existing app session.
- `actorId` in audit logs uses Supabase user_id (UUID), never
  email or display name in the push payload.

## 4. Admin/Dev approval centre

A new tab / panel in `apps/mobile/app/admin-dev.tsx` (admin-
only, gated to Aaron's email per FS-019 auth). Surfaces:

```
┌─ Approval centre ───────────────────────────────┐
│                                                 │
│ Waiting for approval (3)                        │
│   ⚠ EAS Android v21 build                       │
│     Why: deducts 1 build credit (88% used)      │
│     Priority: Health Connect retest             │
│     Default: No build                           │
│     Expires: 2026-05-16 09:30                   │
│     [ Approve ]  [ Defer 24h ]  [ Block ]       │
│                                                 │
│   ⚠ Cloudflare Worker production deploy         │
│     ...                                         │
│                                                 │
│ Deferred (2)        ▸                           │
│ Approved last 7d (5) ▸                          │
│ Blocked / expired (1) ▸                         │
│                                                 │
│ [ Settings: push permission · default expiry ] │
└─────────────────────────────────────────────────┘
```

State transitions from this surface write to:
- Supabase `connector_action_ledger` (or whichever table the
  ledger lives in) via the existing admin-token MCP tool.
- A new MCP tool `project.update_approval_gate(gateId, action)`
  where `action: 'approve' | 'defer' | 'block'` — admin-token-
  gated.

The in-app surface is the canonical write path. Push action
buttons are convenience; tapping them dispatches the same
MCP write under the hood.

## 5. Safety rules

| Action | Approval gate required | Rule cross-ref |
|---|---|---|
| EAS production build (any platform) | YES — every build | Rule 7 |
| Cloudflare Worker production deploy | YES — when deploying to top-level / production env | Rule 7 + this rule |
| Supabase migration on the production project | YES — schema changes touch live data | New: Lane-3 batch per `BACKLOG_AUTOMATION_SYSTEM.md` |
| Public release promotion (App Store / Play Production) | YES — and in addition to internal tester gate | Rule 7 + rule 8 |
| Destructive Supabase mutation (DROP, TRUNCATE, mass UPDATE) | YES | New |
| Force-push to main / reset to remote | YES | Existing git-safety pre-commit + this rule |
| Rotating shared secrets (ATHLETE_MEMORY_API_TOKEN, Supabase service role) | YES | Existing |
| Adding a new public MCP tool | YES — Aaron approves the public surface change | Rule 7 + connector-sanitization rules |

| Action | Approval gate NOT required | Notes |
|---|---|---|
| Doc edit | NO | Standard Lane-1 / Lane-2. |
| Worker preview deploy (`*.workers.dev`) | NO | Not production. Rule 7 still applies if the preview is being promoted. |
| Local typecheck / test runs | NO | Read-only safety. |
| Bridge writeback (`bridge:snapshot` / `project.update_work_status`) | NO | Already gated on rule 12 + admin token. |
| Adding a new docs/spec | NO | Doc lane. |

The safety floor is non-negotiable: **NO production release,
NO EAS build, NO destructive Worker deploy, NO Supabase
migration may proceed past `waiting_for_approval` without an
explicit `approved` event recorded in the ledger.** The
ledger is the audit trail; if no `approved` event exists for
a gate at the time of action, the action is unauthorised.

## 6. Codex handoff prompt — implementation

Stored as ready-to-paste. Aaron MUST explicitly approve
dispatch before this prompt goes to Codex. Until then, this
is documentation only.

```
PROMPT-ID: CODEX-FS-XXX-HUMAN-APPROVAL-GATE-IMPL-01
TYPE: CODEX
LANE: Mobile push + Worker MCP tool + Supabase schema

MCP-FIRST: call project.get_current_state. Bridge → Supabase
direct upsert is LIVE; bridge:snapshot for end-of-task cadence
per rule 12.

Reference (read first):
- docs/HUMAN_APPROVAL_GATE_SPEC.md (this doc — canonical).
- docs/OPERATING_RULES.md § 21 (rule body).
- docs/CONTROL_CENTRE_MVP_SPEC.md § 10 (rule 20 push handoff
  — share the same push wiring).
- apps/mobile/app/admin-dev.tsx § Owner alerts (existing
  in-app banner — extend, don't break).

GOAL
Wire the human-approval push gate end-to-end:
- Supabase: ledger schema extension for ApprovalGate fields.
- Worker: project.update_approval_gate MCP tool (admin
  token).
- Mobile: Admin/Dev approval centre tab, push notification
  trigger sharing rule 20's push wiring.

SCOPE PHASE 1 (this prompt)
1. Supabase migration (additive): extend the action ledger /
   suggestions table with the ApprovalGate fields per § 2 of
   the spec. RLS-gated by admin email allowlist (Aaron only
   can approve). DO NOT touch other tables.
2. Worker: add project.update_approval_gate(gateId, action,
   reason?) tool to /mcp/v2. Admin token required. Validates
   gateState transitions per § 1 state machine. Writes
   updatedAt + actorId + reason to the ledger. Returns the
   updated gate row.
3. Mobile: extend apps/mobile/app/admin-dev.tsx with the
   Approval centre panel per § 4 mockup. Read from
   /api/control_centre or a dedicated /api/approval_gates
   endpoint (admin token). Tap-handlers call
   project.update_approval_gate.
4. Mobile: push notification trigger — share rule 20's
   expo-notifications wiring. Add gate-specific payload per
   § 3.2. iOS notification categories + Android notification
   actions for inline Approve / Defer / Block.
5. Push deep-link handling: lauburu://admin-dev/approval-centre/<gateId>
   opens admin-dev with the panel filtered.

ANTI-RULES
- No public push tokens — admin-only, email-allowlisted.
- No payload PII or raw terminal text.
- Honour rule 11 (MCP-first): never fire push from stale or
  unavailable MCP.
- Honour rule 18 (action ledger): every state transition
  recorded with actorId + reason.
- No EAS build dispatched from this prompt; build approval
  follows Aaron's separate gate per rule 7 (which itself is
  an approval-gate instance once shipped).
- No iOS-only or Android-only — both platforms required for
  parity (rule 14).
- No silent state machine deviations — only the 5 states in
  § 1 are valid.

VERIFICATION
- cd apps/mobile && npx tsc --noEmit clean.
- cd cloudflare-worker && npx tsc --noEmit clean.
- npm run rules:test PASS (21 rules, doc parity).
- npm run mcp:test:public-redaction PASS — gate fields must
  be admin-only on public surfaces; only count + redacted
  summary on /mcp/v2 public-safe tools.
- New contract test: state machine transitions reject
  invalid moves (e.g. expired → approved must fail).
- Manual: simulate waiting_for_approval gate in dev, confirm
  push fires + payload correct + tap action updates ledger.
- Manual: simulate deferred → re-fire after deferred_until.
- Manual: simulate expired → auto-transition to blocked.

OUTPUT (small)
- Status: implementation-complete-awaiting-Agent-confirmation
  / partial / blocked
- Supabase migration name:
- New Worker tool: project.update_approval_gate
- Existing files touched:
- New files added:
- Tests run:
- MCP / bridge writeback evidence:
- Open questions for Aaron / Agent confirmation:
- Recommendation for follow-up (FS-XXX next batch — e.g.
  approval gate templates per action type):
```

Approval-gated: do NOT dispatch this prompt without Aaron's
explicit approval per rule 7 and rule 13. The dispatch itself
is — appropriately — an approval-gate instance.

## 7. Anti-rules

- **No bypassing the gate.** A coder cannot mark a gate
  `approved` on Aaron's behalf, even with admin token. Only
  Aaron's actorId may write `approved`.
- **No silent expiry.** `expired_no_response` MUST be
  surfaced via push at least once before auto-transitioning
  to `blocked` (warning push at 6d for 7d TTL).
- **No hidden gates.** Every approval gate visible in MCP
  must also be visible in the Admin/Dev approval centre.
  Public MCP surfaces show count + redacted summary; admin
  surfaces show full detail.
- **No payload PII.** Push payloads stay redacted per the
  CONNECTOR_SANITIZATION_RULES surface.
- **No production release without explicit approval.**
  Reaffirms rule 7 + rule 8.
- **No EAS build unless Agent-confirmed + Aaron-approved.**
  Reaffirms rule 7. The agent-confirmation gate fires
  BEFORE the approval gate; agent-not-confirmed = investigate
  per rule 6.
- **No destructive deploy / migration without approval.**
  Hard floor.

## 8. Cross-references

- `docs/OPERATING_RULES.md` § 21 — canonical rule body.
- `docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 — rule 20 push
  wiring (same plumbing).
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` § Lane 3 — explicit
  Aaron approval is the Lane-3 gate.
- `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` (FS-019) —
  three-tier auth model that admin email allowlist reuses.
- `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § 5 — manual Aaron
  steps that benefit from this gate (EAS approval / vendor
  console / secret rotation).
- `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
  — payload redaction.
