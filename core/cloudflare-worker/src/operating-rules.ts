/**
 * Operating rules — Worker mirror of docs/OPERATING_RULES.md.
 *
 * The doc is the source of truth. This constant is the live
 * machine-readable mirror that the MCP `project.get_operating_rules`
 * tool and `/api/control_centre.operatingRules` field return.
 *
 * Edit policy: changing this constant requires a paired edit to
 * docs/OPERATING_RULES.md in the same commit. The live integration
 * test asserts count = 23 + each rule's id stays stable. Any
 * promotion / demotion / reorder is a Lane-3 batch with explicit
 * Aaron approval per docs/BACKLOG_AUTOMATION_SYSTEM.md § Lane 3.
 */

export interface OperatingRule {
  id: number;
  title: string;
  body: string;
}

export const OPERATING_RULES: readonly OperatingRule[] = [
  {
    id: 1,
    title: 'Audit → bundles',
    body:
      'After every Agent audit, turn findings into parallel Claude/Codex work bundles in docs/FEEDBACK_SUGGESTIONS.md (FS-XXX candidates).',
  },
  {
    id: 2,
    title: 'Parallel non-overlapping lanes',
    body:
      "Keep both coders (Claude + Codex) working simultaneously in separate, non-overlapping lanes. No coder edits another coder's in-flight files.",
  },
  {
    id: 3,
    title: "Don't stop at one patch",
    body:
      'Continue working through the bundle until materially complete OR genuinely blocked. One passing test is not a stopping point.',
  },
  {
    id: 4,
    title: 'Re-audit on implementation-complete',
    body:
      'When an item is "Implementation-complete, awaiting Agent functional confirmation", re-run the Agent functional audit before any further promotion.',
  },
  {
    id: 5,
    title: 'Agent-confirmed gate',
    body:
      'If the Agent audit confirms, mark "Agent-confirmed, ready for Aaron approval". Do not skip this label.',
  },
  {
    id: 6,
    title: 'Agent-not-confirmed = investigate',
    body:
      'If the Agent audit does NOT confirm, investigate why and continue. Do not silently re-mark.',
  },
  {
    id: 7,
    title: 'EAS build cost control',
    body:
      'No EAS build unless ALL hold: Agent functional audit complete, Agent confirms the change is worthwhile to test on-device, change is bundled, typecheck/tests pass, AND Aaron explicitly approves the build. Default is no build.',
  },
  {
    id: 8,
    title: 'Coders may say "implementation-complete", never "fully done"',
    body:
      'Only Aaron-tested-on-device qualifies as fully done. The four-status sequence (Implementation-complete, awaiting Agent functional confirmation → Agent-confirmed, ready for Aaron build approval → Aaron-approved for EAS build → Built/tester-ready) is mandatory.',
  },
  {
    id: 9,
    title: 'Health/readiness claims stay provisional',
    body:
      'Until direct source data (Apple Health hub / Health Connect hub + verified manual log) supports stronger claims, every reading carries confidence: provisional floor and hedge language only. No "you are ready" / "skip training today" claims.',
  },
  {
    id: 10,
    title: 'Apple Notes is scratchpad only',
    body:
      'Repo docs + MCP + control-centre are the source of truth. Anything intended to drive coder / agent / Aaron action MUST be promoted into the repo-backed flow.',
  },
  {
    id: 11,
    title: 'MCP-first start',
    body:
      'Before any project action or answer, every coder / agent / ChatGPT MUST check the Grappling Map MCP Core state. Order: (1) get_work_status (or mobile.get_work_status / project.get_current_state on /mcp/v2); (2) list_pending_suggestions or project.get_overview; (3) get_automation_state; (4) get_handoff or handoff.get_latest; (5) /api/control_centre if reachable. Then state what MCP says, whether it is fresh or stale (per freshness.staleReason), and only then choose the next task. If MCP is stale (responding but staleness>0), say "MCP stale", use the latest local bridge / terminal / control-centre artefacts as fallback, AND continue fixing MCP canonical sync as a priority. If MCP Core is UNAVAILABLE (not responding, 5xx, or DNS failure), say so clearly, STOP any audit / task / answer that depends on live project state, and do NOT fall back to memory, Apple Notes, screenshots, or old docs unless Aaron explicitly approves a "fallback mode" for that specific question. Never start from memory in any other case.',
  },
  {
    id: 12,
    title: 'Coders run all laptop commands; Aaron approves from phone',
    body:
      'Aaron\'s role is approval, not execution. Coders (Claude / Codex) run every laptop command in docs/CODER_LAPTOP_COMMANDS.md — npm run bridge:snapshot, npm run bridge:verify, cd cloudflare-worker && npx tsc --noEmit, cd cloudflare-worker && wrangler deploy, git add / git commit / git push, all live and contract tests. Aaron NEVER runs typecheck, deploy, bridge:snapshot, or git commands on a laptop. Bridge writeback cadence: after task start, after commit, after blocker, after handoff — the coder MUST run npm run bridge:snapshot (or project.update_work_status) so MCP doesn\'t drift to staleReason: \'no_writeback\'. Coder reports MUST include three explicit fields: MCP update attempted yes/no, bridge snapshot run yes/no, stale reason if blocked. The only steps that stay on Aaron are listed in docs/PHONE_ONLY_AUTOMATION_PLAN.md § 5: FS-XXX approval, EAS build approval, tester-device verification, vendor-console steps, judgement-call decisions, "I tested this on my phone" health-source confirmations, and pasting vendor secrets when they get rotated. Anything else asked of Aaron is a workflow bug — coder fixes the workflow.',
  },
  {
    id: 13,
    title: 'Clear steps; automate first',
    body:
      'When something is required, the worker MUST give Aaron clear step-by-step instructions and automate the step whenever it is safe. Claude / Codex / Agent should be used wherever possible before asking Aaron to act. Aaron should only do secrets, approvals, logins, 2FA, vendor dashboards, or safety-sensitive confirmations. Every output that names follow-up work MUST separate three sections: "automated by coder/agent", "manual Aaron step", and "blocked until Aaron acts". No EAS build may be requested, recommended, prepared, or triggered unless Agent confirms worthwhile on-device testing AND Aaron explicitly approves. Asking Aaron to run a laptop command that a coder can safely run is a workflow bug; the coder runs it, automates it, or reports the exact safety blocker.',
  },
  {
    id: 14,
    title: 'Parallel priorities stay active',
    body:
      'Focused product work (e.g. Grappling Readiness) MUST NOT cause neglect of other active workstreams. The standing parallel priorities are: (a) MCP writeback / no-screenshot workflow, (b) Admin/Dev phone control centre, (c) idle notifications for Claude / Codex / Agent, (d) full automation of laptop commands per rule 12, (e) health input expansion (journal, blood test, DEXA, body composition, spirometry, conditioning machine data, etc.). Coders / Agent MUST surface progress on each parallel priority in every status report — at minimum a one-line freshness note ("MCP writeback: rule 12 cadence holding"), a flag if a parallel priority has gone unmoved for >7 days, and a suggestion for the next safe sub-batch. Pausing a parallel priority requires an explicit Aaron decision recorded in docs/APP_DEVELOPMENTS.md priority order, never a silent drift.',
  },
  {
    id: 15,
    title: 'No-idle dependency',
    body:
      'No worker prompt may have its main action be "wait for another worker to finish." If a next step depends on another worker: (a) put the follow-up inside the same worker\'s prompt when possible, so that worker continues immediately after its own patch; (b) give other workers non-overlapping adjacent work they can do now — tests, bridge / MCP support, schemas, docs, release prep, route-smoke harness, redaction checks, data-model support; (c) if Worker B must verify Worker A\'s output, Worker B prepares the verifier / harness now and then continues into other safe same-lane tasks until Worker A\'s output exists. Every worker prompt MUST include a stay-busy rule per rule 3 AND an explicit alternative non-blocking lane. No coder / agent sits idle because a dependent prompt was split incorrectly. If a coder reports "blocked waiting on X", that is a workflow bug — fix the prompt template, not the worker.',
  },
  {
    id: 16,
    title: 'No delayed instruction chains',
    body:
      'Do not tell Aaron: "After Agent / Codex / Claude returns, run X." Put the follow-up step inside the same worker prompt whenever possible, and tell that worker to execute, prepare, or hand off the next action itself. If a step depends on another worker, the same prompt must include the follow-up action and stop condition. If another worker cannot proceed yet, give it non-blocking adjacent work, not a waiting prompt. If a manual / device action is required from Aaron, make that the only immediate action and store later commands in MCP / bridge / handoff. Use bridge handoff files, AGENT_QA_RESULT_JSON, prompt jobs, or MCP state to preserve next steps so Aaron does not have to remember them. Never make Aaron carry delayed terminal commands in memory while working with other agents.',
  },
  {
    id: 17,
    title: 'Backlog deferred prompts/actions; remove void ones',
    body:
      'Never make Aaron remember delayed instructions. Do not say "after Agent returns, run X" or "after Claude finishes, paste Y" as an untracked instruction. Store deferred prompts / actions in MCP, bridge artifacts, or a local backlog with: id, owner, targetWorker, triggerCondition, promptOrActionText, priority, createdAt, status: pending | active | completed | void | superseded, and voidReason when void. When the trigger condition becomes true, surface the item as the next prompt / action. If the item becomes obsolete, unsafe, replaced, already completed, or irrelevant, mark it void or remove it. Prefer putting follow-up steps inside the same worker prompt so the worker can continue without Aaron. If human / device action is unavoidable, store the later command in the backlog rather than relying on Aaron\'s memory.',
  },
  {
    id: 18,
    title: 'Action ledger until evidence clears',
    body:
      'Every prompt, action, goal, human action, coder action, Agent action, or AI action must be recorded in MCP / bridge until evidence proves it is completed or no longer necessary. **Terminal state is evidence, not memory** — anything discovered in a tmux pane, a build log, an EAS console, a Play Console screen, or any other transient surface MUST be written back to the action ledger / connector_* tables / canonical doc before being considered tracked. Terminal checks must NEVER become the only source of truth. The MCP / action ledger must capture every queued task, deferred prompt, approval gate (rules 21 / 22 / 23), audit finding (per `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md`), and follow-up. A pending action can be cleared only with evidence of completion, supersession, void / obsolete state, unsafe / rejected state, or no-longer-necessary state. Each record should include: id, owner, targetWorkerOrPerson, lane, actionText, triggerCondition, status: pending | active | completed | blocked | void | superseded, priority, createdAt, updatedAt, evidenceSummaryOrLink, and voidReason / supersededBy when applicable. Public MCP surfaces may show compact redacted summaries; full action detail is admin gated. Obsolete Agent prompts, stale worker prompts, and completed bridge commands must be voided or superseded, not left active.',
  },
  {
    id: 19,
    title: 'Coordinator-fed idle lanes',
    body:
      "When Claude, Codex, or Agent is idle, the coordinator (Aaron via ChatGPT or laptop) MUST provide the next highest-leverage prompt for that lane unless a real external blocker or explicit Aaron pause exists. Do not let coders sit idle while active project priorities (per rule 14) remain. The coordinator's pacing obligation is the inverse of rule 15's coder obligation: rule 15 makes individual prompts non-idling-by-design; this rule makes the prompt cadence non-gapping. Idle without a fed prompt for >15 minutes during active workdays is a workflow bug — surface it via project.get_current_state freshness signal and the action ledger backlog (rule 18). Acceptable pause states: tester-device QA awaiting Aaron, EAS billing limit, vendor-console wait, sleep, or explicit Aaron-paused decision recorded in docs/APP_DEVELOPMENTS.md. Unacceptable: \"I forgot to give the coder the next thing.\" If a lane has no high-leverage adjacent work, the coordinator MUST queue a backlog-grooming or doc-refresh prompt rather than leave it idle.",
  },
  {
    id: 20,
    title: 'All-idle notification',
    body:
      "When Claude, Codex, and Agent are all in an `idle` state simultaneously (all three lanes report status: 'idle' via project.get_current_state.agents[].status), the app MUST notify Aaron via a pop-up / banner / push notification. Exclusions: do NOT fire when (a) any lane has a blocker recorded (blockers have their own dedicated alert surface), OR (b) an explicit Aaron pause decision is recorded in docs/APP_DEVELOPMENTS.md priority order. The notification payload MUST include: (1) current top priority title from project.get_current_state.priority; (2) recommended next action drawn from project.list_priorities or the action ledger backlog; (3) timestamp of the all-idle state; (4) freshness check (only fire when MCP is fresh). The notification serves rule 19 (coordinator-fed idle lanes) — it tells Aaron immediately when all coders need a new prompt rather than requiring him to poll the admin-dev surface. In-app banner is implemented (apps/mobile/app/admin-dev.tsx § Owner alerts → \"All-worker direction banner\"); push notification implementation is a Codex follow-up batch (handoff documented in docs/CONTROL_CENTRE_MVP_SPEC.md or equivalent control-centre doc). Honour rule 11 (MCP-first): never fire from stale or unavailable MCP — that would risk a false-idle signal.",
  },
  {
    id: 21,
    title: 'Human-approval push gate',
    body:
      "When automation pauses awaiting Aaron's approval (any prompt or action ledger row with status `waiting_for_approval`), the app MUST send a push notification — even if the app is closed — provided push permissions are granted (per rule 20's push wiring). Notification payload MUST include: (1) what needs approval (action name + brief context, ≤140 chars); (2) why it matters (consequence summary — e.g. 'EAS build deducts X credits' / 'Cloudflare deploy' / 'Supabase row reset'); (3) current top priority for context; (4) safe default if Aaron defers / does nothing (e.g. 'Defer 24h' / 'No build' / 'Stay on current state'); (5) action buttons where the platform supports them (Approve / Defer / Block); fallback is tap-to-open Admin/Dev approval centre. Approval gate state machine: `waiting_for_approval` → `approved` | `deferred` | `expired` | `blocked`. On `approved`: automation resumes from the action ledger / MCP at the exact next step. On `deferred`: gate re-fires after the deferred-until timestamp. On `expired`: gate auto-transitions to `blocked` with reason `expired_no_response`. On `blocked`: gate is closed and a Codex/Claude follow-up prompt is required to advance. Safety floor: NO production release, NO EAS build, NO destructive Worker deploy, NO Supabase migration may proceed past `waiting_for_approval` without an explicit `approved` event recorded in the ledger. Honour rule 7 (EAS build cost control), rule 11 (MCP-first), and rule 18 (action ledger). Spec: docs/HUMAN_APPROVAL_GATE_SPEC.md.",
  },
  {
    id: 22,
    title: 'AI spend gate',
    body:
      "Cheap deterministic / backend / local analysis MUST run first. If a request is likely to require expensive AI inference (long-context reasoning, deep research, multi-pass synthesis, vision-heavy audit, or any path that materially increases monthly AI spend above Aaron's configured threshold), the app MUST notify Aaron via push (sharing rule 21's gate wiring) BEFORE initiating the spend, with the gate UI offering: `approve_in_app` / `defer` / `export_prompt` (paste into external ChatGPT / Claude.ai / etc.) / `ignore`. Cost classes: (1) `free_deterministic` — local rules, regex parsers, MCP reads, bridge:snapshot, parser-only journal-import — runs without ask; (2) `cheap_ai` — short-context calls within the monthly free tier or below the user-configured threshold — runs without ask but is rate-limited per CONNECTOR_SANITIZATION_RULES; (3) `expensive_ai` — long-context reasoning, multi-pass, vision-heavy, or anything beyond the threshold — REQUIRES gate (uses rule 21 state machine: waiting_for_approval → approved | deferred | expired | blocked); (4) `deep_research_external` — work the in-app AI cannot do well or that costs more than the monthly budget — surfaces 'Export prompt' so Aaron can paste into external AI without paying for in-app inference. Notification payload: action name, why it matters, estimated_cost (credits / tokens / dollars), Approve / Defer / Export prompt / Ignore buttons. Settings: per-user monthly AI budget (default $5/month), 'always ask above $X' threshold (default $0.50/call), pay-as-you-go credits (later). Privacy floor: NEVER send raw sensitive data (journal text, health metrics, PII, raw terminal output) to ANY AI inference path (in-app or external) without explicit per-call approval; default for expensive_ai is 'summarize first, send minimal context'. Honour rule 7 (cost control), rule 11 (MCP-first), rule 21 (approval gates). Spec: docs/AI_SPEND_GATES_SPEC.md.",
  },
  {
    id: 23,
    title: 'Deep research offload + artifact cache',
    body:
      "When an `expensive_ai` request (rule 22) classifies as `deep_research_external`, the app MUST: (1) compute a `reuseKey` hash from triggerType + redacted sourceDataSummary; (2) check the research-artifacts cache for a non-stale match — if found, cite the cached artifact via `cited_artifact_id` and skip re-running; (3) if no match, create a research job with status `waiting_for_approval` (rule 21 gate); (4) on `approved`, generate a ready-to-run external-AI prompt (default: ChatGPT Deep Research; configurable) for Aaron to copy-paste; (5) on Aaron's import of the external result, store as a cached artifact indexed by reuseKey, status `cached`, with expiresAt. Future requests matching the same reuseKey reference the cached artifact without re-spending. Schema fields: id, triggerType, prompt (the external-AI-ready prompt), sourceDataSummary (redacted), reuseKey, status (waiting_for_approval | approved | running | imported | cached | stale | blocked), approvedAt, resultArtifactId, expiresAt, citationCount. Triggers: complex journal entry; blood test PDF / DEXA scan; new health trend; readiness anomaly; large visual app audit; long athlete-memory synthesis. Cache rules: NEVER re-run research with a non-stale matching reuseKey; cite the cached artifact in every future explanation that uses it; mark stale after configurable TTL (default 90 days for health context, 30 days for app-state audits). UX: push (per rule 21) with action buttons Approve / Defer / Copy prompt / Import result. Safety: redacted minimal context only; user approval before any sensitive data leaves the app (rule 22 privacy floor); imported result MUST NOT contain medical advice or causation claims (rule 9 + journal-spec § 12 anti-rules); the import path strips any remaining advice/causation language at parse time. Honour rule 7 (cost control), rule 9 (provisional health claims), rule 11 (MCP-first), rule 21 (approval gates), rule 22 (AI-spend ladder). Spec: docs/DEEP_RESEARCH_OFFLOAD_SPEC.md.",
  },
  {
    id: 24,
    title: 'Rule 1 — MCP-first + terminal-truth fallback + no idle lanes',
    body:
      "TOP-PRIORITY RULE. Before every project message, status reply, or audit, the worker / coder / agent / chat lane MUST: (1) check MCP first per rule 11 — call project.get_current_state, mobile.get_lane_overview, or /api/control_centre and report exactly what MCP says, including freshness.isStale, freshness.staleReason, and updatedAt. (2) If MCP is stale (isStale=true, staleReason in {no_writeback, missing_lane, …}) OR if MCP is contradicted by a more recent terminal observation (a lane that MCP says is `working` while terminal evidence shows the prompt has returned and the pane is idle), TREAT TERMINAL TRUTH AS AUTHORITATIVE for that lane and write a bridge:snapshot before responding so the canonical state catches up. Stale cached `working` MUST NEVER suppress an idle-lane prompt. (3) For every lane reported as `idle`, `needs_user`, `needs_review`, `complete_waiting_approval`, or any contradicting-terminal-idle reading, the SAME response MUST include a recommended next prompt for that lane: targetWorker (claude/codex/agent/chat), promptText (or PROMPT-ID summary if the full text is in the action ledger), and an estimated promptProgressPercent if known (otherwise the literal string `unknown`; never silently default to 0%). (4) The MCP / control-centre payload MUST surface, per lane, the structured fields: laneFreshness ('fresh'|'stale'|'unknown'), idleStatus ('idle'|'stale'|'working'|'blocked'|'needs_user'|'needs_review'|'complete_waiting_approval'|'unknown'), recommendedNextPromptTarget (lane id), recommendedNextPromptText (or null if not yet drafted; never fabricated), recommendedNextPromptSummary (≤140 chars), promptProgressPercent (0..100 integer or null/'unknown'). (5) The Admin/Dev lane progress strip and any chat-lane status reply MUST render these structured fields verbatim — no progress is rendered as 0%; missing recommendations render as 'queue a prompt' rather than blank. (6) When this rule and any other rule conflict, this rule wins, except for the rule 7 EAS-build cost gate, the rule 21 human-approval gate, the rule 22 AI-spend gate, and the rule 23 deep-research offload — those four gates remain hard floors that no recommended-next-prompt may bypass. Spec mirrors: docs/OPERATING_RULES.md (preamble + this rule), docs/CONTROL_CENTRE_LANE_PROGRESS.md.",
  },
] as const;

export const OPERATING_RULES_DOC_PATH = 'docs/OPERATING_RULES.md';

/** Public-safe summary suitable for /api/control_centre. */
export interface OperatingRulesSummary {
  count: number;
  ids: readonly number[];
  titles: readonly string[];
  docPath: string;
}

export function buildOperatingRulesSummary(): OperatingRulesSummary {
  return {
    count: OPERATING_RULES.length,
    ids: OPERATING_RULES.map((r) => r.id),
    titles: OPERATING_RULES.map((r) => r.title),
    docPath: OPERATING_RULES_DOC_PATH,
  };
}

/** Full payload for the MCP project.get_operating_rules tool. */
export function buildOperatingRulesPayload() {
  return {
    schemaVersion: 1 as const,
    generatedAt: new Date().toISOString(),
    docPath: OPERATING_RULES_DOC_PATH,
    rules: OPERATING_RULES.map((r) => ({ id: r.id, title: r.title, body: r.body })),
    safety: {
      publicSafe: true,
      privateFieldsWithheld: false,
      note: 'Operating rules are intentionally public; they describe coder discipline, not project internals.',
    },
  };
}
