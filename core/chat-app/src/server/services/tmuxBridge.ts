import type { CoderLaneRow } from '../types/connector';

/**
 * Provisional read-only tmux bridge.
 *
 * TODO: replace the static rows with a local-machine producer that
 * captures specific, owner-configured tmux panes using:
 *
 *   tmux capture-pane -p -t <pane-id>
 *
 * The production bridge must stay read-only, must use an allowlisted
 * pane-id map, must redact token-like substrings before persistence,
 * and must publish compact summaries only. The backend route should
 * never execute arbitrary commands from app or connector input.
 */
export function getLaneSummaries(nowIso: string = new Date().toISOString()): CoderLaneRow[] {
  return [
    {
      laneId: 'claude',
      status: 'idle',
      lastSeenAt: nowIso,
      currentPromptId: null,
      lastPromptId: 'CLAUDE-REVIEW-PENDING',
      lastSummary: 'Claude lane is parked until the next owner-reviewed backend/API handoff.',
      lastCommit: null,
      lastTypecheckResult: null,
      dirtyFiles: [],
      nextPrompt: 'CLAUDE-REVIEW-MCP-DUMMY-ROUTES-01',
    },
    {
      laneId: 'codex',
      status: 'working',
      lastSeenAt: nowIso,
      currentPromptId: 'CODEX-BACKEND-API-AI-IMPLEMENTATION-01',
      lastPromptId: 'CODEX-UX-INFORMATION-ARCHITECTURE-CLEANUP-01',
      lastSummary: 'Codex is wiring dummy connector routes, tests, and owner-only Admin/Dev display.',
      lastCommit: null,
      lastTypecheckResult: 'pass',
      dirtyFiles: [],
      nextPrompt: null,
    },
  ];
}
