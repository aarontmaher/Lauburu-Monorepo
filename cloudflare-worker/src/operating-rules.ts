/**
 * Operating rules — Worker mirror of docs/OPERATING_RULES.md.
 *
 * The doc is the source of truth. This constant is the live
 * machine-readable mirror that the MCP `project.get_operating_rules`
 * tool and `/api/control_centre.operatingRules` field return.
 *
 * Edit policy: changing this constant requires a paired edit to
 * docs/OPERATING_RULES.md in the same commit. The live integration
 * test asserts count = 15 + each rule's id stays stable. Any
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
      'Before starting any new task, every coder / agent / ChatGPT MUST check the MCP / control-centre state. Order: (1) get_work_status (or mobile.get_work_status / project.get_current_state on /mcp/v2); (2) list_pending_suggestions or project.get_overview; (3) get_automation_state; (4) get_handoff or handoff.get_latest; (5) /api/control_centre if reachable. Then state what MCP says, whether it is fresh or stale (per freshness.staleReason), and only then choose the next task. If MCP is stale, say "MCP stale", use latest terminal / control-centre state as fallback, AND continue fixing MCP canonical sync as a priority. Never start from memory, Apple Notes, screenshots, or old docs unless MCP / control-centre is unavailable.',
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
