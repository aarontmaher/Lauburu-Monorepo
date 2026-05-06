/**
 * Agent-status client — reads per-agent "Claude finished X" /
 * "Codex blocked on Y" rows from the admin-token-gated backend
 * route `GET /api/athlete-memory/admin/agent-status`. Owner-only
 * by route gate.
 *
 * No write path on this client — agent-status writes happen
 * server-side via `scripts/mark-agent-done.sh` (or, future,
 * the connector write tools per
 * docs/CONNECTOR_BACKLOG_TOOLS_PLAN.md).
 *
 * Local-only consumer pattern: the mobile Admin/Dev card polls
 * this on mount + every N seconds. Never persists the response.
 */

export interface AgentStatusEntry {
  agent: string;
  status: 'done' | 'blocked' | 'needs_review' | 'in_progress' | 'unknown' | string;
  task: string;
  summary: string;
  verification: string;
  nextAction: string;
  updatedAt: string | null;
}

export interface AgentStatusResponse {
  ok: boolean;
  generatedAt: string;
  agents: Record<string, AgentStatusEntry | null>;
}

/**
 * Pull the latest agent-status snapshot. Caller MUST handle null
 * (no env / no auth) because the helper does not throw — the
 * Admin/Dev card just renders the last good snapshot until the
 * next poll succeeds.
 */
export async function fetchAgentStatus(): Promise<AgentStatusResponse | null> {
  try {
    const apiBase = (process.env.EXPO_PUBLIC_AI_PUBLIC_URL ?? '').replace(/\/$/, '');
    const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
    if (!apiBase || !memToken) return null;
    const res = await fetch(`${apiBase}/admin/agent-status`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'x-athlete-memory-token': memToken,
      },
    });
    if (!res.ok) return null;
    const data = (await res.json()) as AgentStatusResponse;
    if (!data || data.ok !== true) return null;
    return data;
  } catch {
    return null;
  }
}
