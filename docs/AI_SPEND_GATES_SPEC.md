# AI spend gates — spec (operating rule 22)

Cheap deterministic / backend / local analysis runs first.
Expensive AI inference (long-context reasoning, deep research,
multi-pass synthesis, vision-heavy audit) requires a per-call
approval gate that surfaces estimated cost, lets Aaron approve
in-app, defer, export the prompt for external AI, or ignore.
The privacy floor: NO raw sensitive data is sent to any AI
inference path without explicit per-call approval.

This is **spec only**. No app code. No Worker code change. No
EAS build. Implementation is a Codex follow-up batch gated on
Aaron approval (per rule 7 + rule 13 + rule 21).

## 0. Relationship to existing rules

| Rule | Relationship |
|---|---|
| Rule 7 (EAS build cost control) | Rule 22 generalises the cost-gating principle from EAS builds to AI inference. EAS-build approval is one specific instance of an approval gate (rule 21); AI-spend gates are another. |
| Rule 11 (MCP-first) | The cheap-first ladder ALWAYS starts with MCP reads / local artefacts. AI inference is never the first step. |
| Rule 21 (Human-approval push gate) | Rule 22 reuses rule 21's state machine + push wiring. An `expensive_ai` call is a `waiting_for_approval` gate with payload-specific fields (cost class, estimated cost, prompt summary). |
| Rule 18 (action ledger) | AI spend events are recorded as ledger rows with cost actuals after the call completes. |
| Rule 9 (provisional health claims) | AI-derived health observations remain `confidence: provisional` until calibration window + Aaron approval per rule 9. The AI-spend gate doesn't change the health-claim ladder. |

## 1. Cost classes

The decision ladder. Always step from class 1 to higher classes;
never start at class 3 when class 1 would answer the question.

### 1.1 `free_deterministic`

Runs without ask, without rate limit, without cost.

- Local rules / regex parsers (e.g. FS-020 journal-import parser,
  date heuristics, dose unit detection).
- MCP reads: `project.get_current_state`, `mobile.get_*`,
  `handoff.get_latest`, `qa.get_latest_result`, etc.
- `bridge:snapshot`, `bridge:verify`, `bridge:agent-qa`.
- Local Worker handlers (anything that runs on the existing
  Cloudflare Worker without invoking an external AI API).
- Pre-aggregated stats from Supabase (counts, sums, ratios).
- Static dictionary lookups (`journal-canonical-terms.ts`,
  `journal-research-snippets.ts`).
- Pure compute over already-fetched data (e.g. macro ratio
  derivation, confidence scoring per FS-018 § 8).

Decision: **always run first.** No gate. Result is logged but no
ledger row required (it's not a spend event).

### 1.2 `cheap_ai`

Runs without ask but is rate-limited and metered.

- Short-context LLM calls (≤4k tokens prompt, ≤500 token output)
  within the monthly free tier.
- Calls that fall under the user-configured "always ask above
  $X" threshold (default $0.50/call).
- Pattern: short summarisation, classification, a single Q+A
  over an already-redacted context.

Decision: **runs without ask, BUT**
- Rate limit per user: 60 calls / hour (configurable).
- Logged as an action ledger row with `cost_class: 'cheap_ai'`,
  `estimated_cost`, `actual_cost`, `tokens_in`, `tokens_out`.
- Aborts if monthly budget cap hit (transitions to `expensive_ai`
  gate or `deep_research_external` export-only path).
- Inputs are sanitised via the redaction rules in
  `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
  before being sent.

### 1.3 `expensive_ai`

REQUIRES gate. Uses rule 21 state machine.

- Long-context calls (≥4k tokens prompt OR ≥500 token output).
- Multi-pass synthesis (chained calls; agentic flows; tool-use
  loops).
- Vision-heavy calls (image / screenshot analysis).
- Any call whose `estimated_cost` exceeds the user-configured
  threshold (default $0.50/call).
- Any call that pushes monthly usage above the budget cap.

Decision: **gate.** Push notification fires per rule 21. Aaron
chooses Approve in-app / Defer / Export prompt / Ignore. On
Approve: call runs, ledger row written. On Defer: call queued
for `deferred_until`. On Export prompt: prompt is rendered as
copy-pasteable text for external AI; no in-app spend. On Ignore:
gate closes; no spend.

### 1.4 `deep_research_external`

Surface "Export prompt" by default — never spend in-app.

- Tasks that an in-app LLM can't do well (extended deep research,
  long-form synthesis, multi-source citation gathering).
- Tasks that would exceed the monthly budget if run in-app.
- Tasks where Aaron explicitly prefers external AI for
  observability (paste into ChatGPT / Claude.ai / Gemini and
  read the conversation in their UI).

Decision: **always export-by-default.** The gate UI surfaces a
copy-pasteable prompt; no in-app inference is initiated. If
Aaron explicitly chooses "approve_in_app" override, the call
escalates to `expensive_ai` flow.

## 2. Trigger examples

These are concrete examples of when each cost class applies in
the Lauburu app. The enforcement logic lives in a router (Codex
batch); the table below is the spec input.

| Action | Likely class | Reason |
|---|---|---|
| Parse Apple Notes paste into journal events | `free_deterministic` | Pure regex / dictionary lookup. |
| Look up "amitriptyline" in shared dictionary | `free_deterministic` | Static const. |
| Compute macro ratios for a `nutrition_daily_log` row | `free_deterministic` | Pure math. |
| 1-line "Did you mean BPC-157?" suggestion | `cheap_ai` | Short fuzzy match; rate-limited. |
| Summarise the last 7 days of journal entries into a 200-word "what's been happening" card | `expensive_ai` | Long context (7d × ~10 events × notes), summarisation. Gate. |
| Synthesise "do my macro ratios correlate with sleep over 14 days?" | `expensive_ai` | Multi-day cross-correlation; rule 8 + rule 9 honoured (provisional + low confidence). Gate. |
| New trend in HRV / RHR / sleep efficiency over 30 days | `expensive_ai` | Long context. Gate. |
| Blood test PDF / DEXA scan upload + interpretation | `expensive_ai` | Vision + long context. Gate. |
| Readiness anomaly: Coach detects unusual pattern, asks AI to explain | `expensive_ai` | Multi-source synthesis. Gate. |
| Large visual audit (multiple screenshots) | `expensive_ai` | Vision. Gate. |
| Long athlete-memory synthesis (months of data) | `expensive_ai` | Very long context. Gate. |
| "Research BPC-157 mechanism in detail" | `deep_research_external` | Better suited to external AI; export prompt. |
| "Compare Aaron's training load to grappling literature" | `deep_research_external` | Web research; export prompt. |

## 3. Notification UX (extends rule 21's payload)

When an `expensive_ai` gate fires, the push payload extends rule
21's standard payload with cost-specific fields:

```ts
{
  title: `AI spend approval: ${actionName}`,
  body: `${whyItMatters} · Estimated cost: ${estimatedCostString} · Top priority: ${topPriorityContext}`,
  data: {
    gateId: string,
    gateState: 'waiting_for_approval',
    costClass: 'expensive_ai' | 'deep_research_external',
    estimatedCost: { credits?: number, tokensIn?: number, tokensOut?: number, dollars?: number },
    estimatedCostString: string,        // e.g. "~$0.85" or "~12k tokens"
    monthlyBudgetUsedPct: number,       // e.g. 0.42 = 42% of the month's budget consumed
    promptSummary: string,              // ≤280 chars; redacted summary of what the prompt asks
    sensitiveDataIncluded: boolean,     // true if the prompt would include redacted-by-design fields the user MUST opt into
    expiresAt: string,
    deepLink: 'lauburu://admin-dev/ai-spend/<gateId>',
    freshnessSnapshot: { isFresh: boolean },
  },
  actions: [
    { id: 'approve_in_app', title: 'Approve' },
    { id: 'defer',          title: 'Defer' },
    { id: 'export_prompt',  title: 'Export prompt' },
    { id: 'ignore',         title: 'Ignore' },
  ],
}
```

Where the platform doesn't render 4 inline actions, the fallback
is tap-to-open the AI-spend approval centre filtered to the gate.

## 4. Settings — per-user

Lives in the user's own profile (Supabase `user_settings` or
similar). Rule 22 settings:

```ts
interface AiSpendSettings {
  monthlyBudgetUsd: number;             // default $5
  alwaysAskAboveUsd: number;            // default $0.50/call
  alwaysAskAboveTokens: number;         // default 4000 (long-context threshold)
  payAsYouGoEnabled: boolean;           // default false (later)
  payAsYouGoCreditsCents: number;       // default 0
  defaultExportInsteadOfApprove: boolean; // default true for deep_research_external; off for expensive_ai
  monthlyResetDayOfMonth: number;       // 1
  currentMonth: { spendUsd: number; calls: number; lastResetAt: string };
}
```

The Admin/Dev settings panel exposes these controls; the user
profile screen exposes a subset (budget + threshold) for self-
service.

## 5. Privacy / safety floor

**Hard rules — never bypassed without explicit per-call approval.**

1. **Raw sensitive data NEVER leaves the device / Supabase
   without per-call approval.** This includes journal text,
   per-day health metrics, PII, raw terminal output, screenshots
   of personal data, and the body of `metric_effect_windows`.
2. **Default summarisation pipeline.** When an `expensive_ai`
   call is approved, the default flow is:
   (a) build a structured, redacted context block (counts,
       ratios, dates — never raw text);
   (b) include a `sensitiveDataIncluded: false` flag in the
       gate's metadata;
   (c) only when Aaron explicitly opts into "include raw
       context" does the call include unredacted journal /
       health text — and that opt-in is per-call, not session
       or global.
3. **External AI export NEVER includes secrets.** Worker tokens,
   Supabase service role, EAS tokens, etc. are filtered out by
   `CONNECTOR_SANITIZATION_RULES`.
4. **No AI inference over `journal_aggregate_*` cross-user data
   without aggregation thresholds** (FS-020 § 9). Aggregate
   reads are gated separately; AI summarisation over them
   inherits both gates.
5. **Logging hygiene.** AI request/response logs are admin-token-
   gated; never appear on public MCP surfaces.

## 6. Codex handoff prompt — implementation

Stored as ready-to-paste. Aaron MUST explicitly approve dispatch
before this prompt goes to Codex. Until then, this is documentation
only.

```
PROMPT-ID: CODEX-FS-XXX-AI-SPEND-GATES-IMPL-01
TYPE: CODEX
LANE: AI-spend router + Worker MCP tool + Supabase settings + mobile settings UI

MCP-FIRST: call project.get_current_state. Bridge → Supabase
direct upsert is LIVE; bridge:snapshot for end-of-task cadence
per rule 12.

Reference (read first):
- docs/AI_SPEND_GATES_SPEC.md (this doc — canonical).
- docs/HUMAN_APPROVAL_GATE_SPEC.md (rule 21 — state machine
  + push wiring this rule reuses).
- docs/OPERATING_RULES.md § 22 (rule body).
- cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md
  (privacy floor).

GOAL
Wire the AI-spend gate end-to-end:
- Supabase: user_settings extension with AiSpendSettings.
- Worker: project.classify_ai_call(prompt, context_size,
  vision_count) -> { cost_class, estimated_cost,
  needs_approval } MCP tool. Reuse existing approval-gate
  ledger schema from rule 21.
- Mobile: AI-spend approval centre panel (in admin-dev OR
  user settings — ship admin-dev first per FS-019 auth
  model). 4-button gate UI per § 3.
- Mobile: prompt-export modal that renders the redacted
  prompt as copy-pasteable text (markdown with code fences).
- Local cost estimator: input length + model + vision count
  -> estimated_cost (dollars + tokens). Lives in mobile +
  Worker for parity.

SCOPE PHASE 1 (this prompt)
1. Supabase migration (additive): user_settings table /
   columns for AiSpendSettings per § 4. RLS-gated by
   auth.uid().
2. Worker: project.classify_ai_call MCP tool (admin token).
   Returns the cost class + estimated cost + needs_approval
   flag for a given input description. Pure function — no
   AI call from this tool.
3. Mobile: ai-spend-store (zustand or similar) tracking
   monthly spend, current settings, gate state.
4. Mobile: AI-spend approval centre panel in admin-dev with
   4-button gate UI. Reuses rule 21's gate state machine.
5. Mobile: prompt-export modal for export_prompt action.
6. Mobile: cost estimator local function.
7. Tests: classifier returns expected class for the trigger
   examples in § 2.

ANTI-RULES
- No payload PII in push or log surfaces.
- No raw sensitive data sent to any AI without per-call
  approval; default is summarised redacted context.
- Honour rule 11 (MCP-first): cost-class classification
  reads from MCP/local first.
- Honour rule 21: reuse the approval-gate state machine
  exactly; no parallel state model.
- No public-write tools — gate updates are admin-token-gated.
- No EAS build dispatched from this prompt.
- No iOS-only or Android-only.

VERIFICATION
- cd apps/mobile && npx tsc --noEmit clean.
- cd cloudflare-worker && npx tsc --noEmit clean.
- npm run rules:test PASS (22 rules, doc parity).
- npm run mcp:test:public-redaction PASS.
- New contract test: classifier returns expected class for
  each row in § 2 trigger examples table.
- Manual: simulate expensive_ai trigger, confirm push fires
  + 4 buttons + Approve runs the call + Export shows the
  prompt + Defer queues + Ignore closes.
- Manual: confirm monthly budget cap aborts further
  expensive_ai calls until next month.

OUTPUT (small)
- Status: implementation-complete-awaiting-Agent-confirmation
  / partial / blocked
- Supabase migration name:
- New Worker tool: project.classify_ai_call
- Existing files touched:
- New files added:
- Tests run:
- MCP / bridge writeback evidence:
- Open questions for Aaron / Agent confirmation:
- Recommendation for follow-up (FS-XXX next batch — e.g.
  pay-as-you-go credits flow):
```

Approval-gated: do NOT dispatch this prompt without Aaron's
explicit approval per rule 7 + rule 13 + rule 21.

## 7. Anti-rules

- **No starting at class 3.** Cheap deterministic must be
  attempted first. Skipping the ladder is a bug.
- **No silent escalation.** A cheap_ai call hitting its rate
  limit must surface a gate, not silently degrade.
- **No bypassing the privacy floor.** Per-call approval for raw
  data is non-negotiable; no "trusted session" mode.
- **No background AI calls without budget tracking.** Every AI
  inference is logged with cost_class + estimated_cost + actual_cost.
- **No public push tokens.** Admin-only / email-allowlisted per
  FS-019.
- **No PII in push payloads.** Redacted summary only; full
  prompt only opens via deep-link inside the app.
- **No medical advice from AI summaries.** Rule 9 + the journal
  spec § 12 anti-rules apply to AI output too.

## 8. Cross-references

- `docs/OPERATING_RULES.md` § 22 — canonical rule body.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 state machine
  + push wiring (reused).
- `docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 — rule 20 push wiring
  (shared plumbing).
- `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
  — privacy floor.
- `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` (FS-019) —
  three-tier auth model.
- `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md` § 6 + § 8 —
  research-background disclosure + pattern engine; rule 22
  governs ANY AI inference layered on top.
- `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` — confidence
  + missingness copy AI-derived insights MUST honour.
