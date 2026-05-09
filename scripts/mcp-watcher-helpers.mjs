/**
 * Pure helpers for mcp-watcher.mjs. Kept separate so they
 * can be imported by a test without spawning HTTP fetches
 * or tmux subprocesses.
 *
 * Two responsibilities:
 *   1. Classify the MCP freshness signal into actionable
 *      buckets (fresh / stale_writeback / no_writeback /
 *      env_missing / unreachable).
 *   2. Detect terminal-vs-MCP disagreement: when MCP says a
 *      lane is `working` but the tmux pane shows the lane
 *      is idle (no spinner, prompt visible), the cached
 *      `agent.status` is unreliable per the mcpLivenessP0
 *      rule.
 *
 * Helpers return STRUCTURED VERDICTS (no I/O), so the
 * orchestrator script can decide whether to log, auto-
 * refresh, or escalate.
 */

export const FRESHNESS_WINDOW_MS = 10 * 60 * 1000;
export const TERMINAL_IDLE_MARKERS = [
  'auto mode on',
  'bypass permissions on',
  'Press up to edit queued messages',
];
export const TERMINAL_BUSY_MARKERS = [
  'Running…',
  'Working ',
  '✶ ',
  '✳ ',
  '⎿  Running',
  'esc to interrupt',
  'timeout 10m',
  'Photosynthesizing',
  'Cooked for ',
  'Gusting',
  '✻ ',
];

/**
 * Classify a freshness payload returned by
 * project.get_current_state.freshness.
 *
 * @param {object|null} freshness — { isFresh?, staleReason?, ageMs?, updatedAt? }
 * @param {object} [opts] — { httpStatus?: number, networkError?: boolean }
 * @returns {{ verdict: 'fresh'|'stale_writeback'|'no_writeback'|'env_missing'|'unreachable', actionable: boolean, reason: string }}
 */
export function classifyFreshness(freshness, opts = {}) {
  if (opts.networkError) {
    return { verdict: 'unreachable', actionable: true, reason: 'network error reaching MCP Worker' };
  }
  if (typeof opts.httpStatus === 'number' && opts.httpStatus >= 500) {
    return { verdict: 'unreachable', actionable: true, reason: `MCP Worker returned ${opts.httpStatus}` };
  }
  if (!freshness || typeof freshness !== 'object') {
    return { verdict: 'unreachable', actionable: true, reason: 'freshness payload missing' };
  }
  const reason = typeof freshness.staleReason === 'string' ? freshness.staleReason : null;
  if (reason === 'fresh') {
    return { verdict: 'fresh', actionable: false, reason: 'within freshness window' };
  }
  if (reason === 'env_missing') {
    return {
      verdict: 'env_missing',
      actionable: true,
      reason: 'Worker not configured — missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY secrets',
    };
  }
  if (reason === 'no_writeback') {
    return {
      verdict: 'no_writeback',
      actionable: true,
      reason: 'bridge:snapshot has never written to connector_work_status',
    };
  }
  if (reason === 'stale_writeback') {
    const ageMin = typeof freshness.ageMs === 'number'
      ? Math.round(freshness.ageMs / 60_000)
      : null;
    return {
      verdict: 'stale_writeback',
      actionable: true,
      reason: ageMin !== null
        ? `bridge:snapshot last wrote ${ageMin} min ago (window 10 min)`
        : 'bridge:snapshot wrote outside the freshness window',
    };
  }
  return { verdict: 'unreachable', actionable: true, reason: `unknown staleReason: ${reason}` };
}

/**
 * Classify a tmux pane's text as idle vs busy.
 * Mirrors the heuristic in scripts/bridge-snapshot-lanes.sh
 * status classifier.
 */
export function classifyPaneText(paneText) {
  if (typeof paneText !== 'string' || paneText.length === 0) {
    return { paneStatus: 'unknown', reason: 'empty or missing pane text' };
  }
  const tail = paneText.split('\n').slice(-25).join('\n');
  for (const marker of TERMINAL_BUSY_MARKERS) {
    if (tail.includes(marker)) {
      return { paneStatus: 'busy', reason: `busy marker present: ${marker.trim()}` };
    }
  }
  for (const marker of TERMINAL_IDLE_MARKERS) {
    if (tail.includes(marker)) {
      return { paneStatus: 'idle', reason: `idle marker present: ${marker.trim()}` };
    }
  }
  return { paneStatus: 'unknown', reason: 'no idle or busy marker matched' };
}

/**
 * Detect disagreement between cached MCP agent.status and
 * observed tmux pane state.
 *
 * Per mcpLivenessP0 rule: when freshness !== 'fresh', the
 * cached agent.status is unreliable and the UI MUST show
 * stale/unknown, not working. This function exposes the
 * disagreement so a watcher / Admin/Dev surface / push
 * handler can act on it.
 *
 * @param {{ id: string, status: string }} cachedAgent
 * @param {{ paneStatus: 'busy'|'idle'|'unknown', reason: string }} paneVerdict
 * @returns {{ disagrees: boolean, reason: string, suggestedTrueStatus: string }}
 */
export function detectAgentDisagreement(cachedAgent, paneVerdict) {
  if (!cachedAgent || typeof cachedAgent !== 'object') {
    return { disagrees: false, reason: 'no cached agent provided', suggestedTrueStatus: 'unknown' };
  }
  const cached = typeof cachedAgent.status === 'string' ? cachedAgent.status : 'unknown';
  if (paneVerdict.paneStatus === 'unknown') {
    return { disagrees: false, reason: 'pane status unknown — cannot disagree', suggestedTrueStatus: cached };
  }
  if (cached === 'working' && paneVerdict.paneStatus === 'idle') {
    return {
      disagrees: true,
      reason: `MCP cached working but pane idle — ${paneVerdict.reason}`,
      suggestedTrueStatus: 'idle',
    };
  }
  if (cached === 'idle' && paneVerdict.paneStatus === 'busy') {
    return {
      disagrees: true,
      reason: `MCP cached idle but pane busy — ${paneVerdict.reason}`,
      suggestedTrueStatus: 'working',
    };
  }
  return {
    disagrees: false,
    reason: 'cached and pane agree',
    suggestedTrueStatus: cached,
  };
}

/**
 * Decide whether to auto-refresh (run bridge:snapshot).
 *
 * Default policy:
 *   - fresh                → no
 *   - env_missing          → no (can't fix from here)
 *   - unreachable          → no (network/server problem)
 *   - no_writeback         → yes (bridge has never run)
 *   - stale_writeback      → yes (bridge overdue)
 *
 * Auto-refresh is OFF by default in the orchestrator;
 * --auto-refresh flag opts in.
 */
export function shouldAutoRefresh(freshnessVerdict) {
  if (!freshnessVerdict || typeof freshnessVerdict !== 'object') return false;
  return freshnessVerdict.verdict === 'no_writeback' || freshnessVerdict.verdict === 'stale_writeback';
}

/**
 * Build the structured finding written to the JSONL log +
 * (optionally) connector_handoff.auditFindings.
 */
export function buildFinding({ freshnessVerdict, agentDisagreements, observedAt }) {
  return {
    schemaVersion: 1,
    observedAt,
    freshness: freshnessVerdict,
    agentDisagreements: agentDisagreements ?? [],
    actionable: !!freshnessVerdict?.actionable || (agentDisagreements ?? []).length > 0,
  };
}
