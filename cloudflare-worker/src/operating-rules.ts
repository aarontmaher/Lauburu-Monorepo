/**
 * Operating rules — Worker mirror of docs/OPERATING_RULES.md.
 *
 * The doc is the source of truth. This constant is the live
 * machine-readable mirror that the MCP `project.get_operating_rules`
 * tool and `/api/control_centre.operatingRules` field return.
 *
 * Edit policy: changing this constant requires a paired edit to
 * docs/OPERATING_RULES.md in the same commit. The live integration
 * test asserts count = 10 + each rule's id stays stable. Any
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
