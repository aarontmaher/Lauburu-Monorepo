import { AI_PUBLIC_BASE, MCP_BASE_URL } from './ai-backend-config';

/**
 * Thin JSON-RPC 2.0 client for the unified Lauburu MCP v2 endpoint
 * (POST /mcp/v2). Used by the Admin/Dev tab's "MCP Live" + diagnostics
 * panels.
 *
 * Reuses EXPO_PUBLIC_MCP_BASE_URL (auto-appends `/mcp/v2`) so the
 * existing connector-status-client.ts and this client share the same
 * base. The admin token (`EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`) is sent
 * on every call — the v2 server fail-softs admin tools to a
 * tool-result error when the token is missing, so the UI can render
 * a clear "admin needed" state instead of crashing.
 *
 * NEVER renders the token in the UI. NEVER logs it.
 */

export interface McpV2Tool {
  name: string;
  description: string;
  inputSchema?: unknown;
}

export interface McpV2CallEnvelope {
  ok: true;
  isError: boolean;
  text: string;
  payload: unknown;
}

export interface McpV2CallFailure {
  ok: false;
  reason: 'transport' | 'rpc_error' | 'no_content' | 'parse_error' | 'mcp_base_url_missing';
  message: string;
  status?: number;
}

export type McpV2CallResult = McpV2CallEnvelope | McpV2CallFailure;

function v2BaseUrl(): string | null {
  if (MCP_BASE_URL) {
    const trimmed = MCP_BASE_URL.replace(/\/$/, '');
    // EXPO_PUBLIC_MCP_BASE_URL may already end at /api or be the worker
    // root. We want the v2 endpoint at <root>/mcp/v2.
    const base = trimmed.endsWith('/api') ? trimmed.slice(0, -'/api'.length) : trimmed;
    return `${base}/mcp/v2`;
  }
  // Fall back to deriving from AI_PUBLIC_BASE only when the public
  // backend is configured (legacy Railway shape). Most testers won't
  // have this — return null so the UI renders "MCP not configured".
  if (AI_PUBLIC_BASE) {
    const publicBase = AI_PUBLIC_BASE.replace(/\/$/, '').replace(/\/athlete-memory$/, '');
    return `${publicBase}/mcp/v2`;
  }
  return null;
}

async function rpc(body: unknown, signal?: AbortSignal): Promise<{ status: number; raw: string } | { error: string }> {
  const url = v2BaseUrl();
  if (!url) return { error: 'mcp_base_url_missing' };
  const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
  try {
    const res = await fetch(url, {
      method: 'POST',
      signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(memToken ? { 'x-athlete-memory-token': memToken } : {}),
      },
      body: JSON.stringify(body),
    });
    const raw = await res.text();
    return { status: res.status, raw };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'unknown_error' };
  }
}

export async function mcpV2InitializeAndListTools(signal?: AbortSignal): Promise<{
  ok: true;
  serverInfo: { name: string; version: string; description?: string };
  protocolVersion: string;
  tools: McpV2Tool[];
} | McpV2CallFailure> {
  const initRes = await rpc(
    {
      jsonrpc: '2.0', id: 1, method: 'initialize',
      params: { protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'lauburu-mobile', version: '0.1.0' } },
    },
    signal,
  );
  if ('error' in initRes) {
    return { ok: false, reason: initRes.error === 'mcp_base_url_missing' ? 'mcp_base_url_missing' : 'transport', message: initRes.error };
  }
  if (initRes.status !== 200) {
    return { ok: false, reason: 'rpc_error', message: `initialize → HTTP ${initRes.status}`, status: initRes.status };
  }
  let initParsed: { result?: { protocolVersion?: string; serverInfo?: { name?: string; version?: string; description?: string } }; error?: { message?: string } };
  try { initParsed = JSON.parse(initRes.raw); } catch { return { ok: false, reason: 'parse_error', message: 'initialize body not JSON' }; }
  if (initParsed.error) return { ok: false, reason: 'rpc_error', message: initParsed.error.message ?? 'initialize error' };

  const listRes = await rpc({ jsonrpc: '2.0', id: 2, method: 'tools/list' }, signal);
  if ('error' in listRes) return { ok: false, reason: 'transport', message: listRes.error };
  if (listRes.status !== 200) return { ok: false, reason: 'rpc_error', message: `tools/list → HTTP ${listRes.status}`, status: listRes.status };
  let listParsed: { result?: { tools?: McpV2Tool[] }; error?: { message?: string } };
  try { listParsed = JSON.parse(listRes.raw); } catch { return { ok: false, reason: 'parse_error', message: 'tools/list body not JSON' }; }
  if (listParsed.error) return { ok: false, reason: 'rpc_error', message: listParsed.error.message ?? 'tools/list error' };
  const tools = listParsed.result?.tools ?? [];
  const info = initParsed.result?.serverInfo ?? {};
  return {
    ok: true,
    serverInfo: { name: info.name ?? 'unknown', version: info.version ?? '0', description: info.description },
    protocolVersion: initParsed.result?.protocolVersion ?? 'unknown',
    tools,
  };
}

export async function mcpV2CallTool(name: string, args: unknown = {}, signal?: AbortSignal): Promise<McpV2CallResult> {
  const callRes = await rpc(
    { jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name, arguments: args ?? {} } },
    signal,
  );
  if ('error' in callRes) {
    return { ok: false, reason: callRes.error === 'mcp_base_url_missing' ? 'mcp_base_url_missing' : 'transport', message: callRes.error };
  }
  if (callRes.status !== 200) {
    return { ok: false, reason: 'rpc_error', message: `tools/call → HTTP ${callRes.status}`, status: callRes.status };
  }
  let parsed: { result?: { content?: Array<{ text?: string; type?: string }>; isError?: boolean }; error?: { message?: string } };
  try { parsed = JSON.parse(callRes.raw); } catch { return { ok: false, reason: 'parse_error', message: 'tools/call body not JSON' }; }
  if (parsed.error) return { ok: false, reason: 'rpc_error', message: parsed.error.message ?? 'tools/call error' };
  const text = parsed.result?.content?.[0]?.text ?? '';
  if (!text) return { ok: false, reason: 'no_content', message: 'tools/call returned no content' };
  let payload: unknown = text;
  try { payload = JSON.parse(text); } catch { /* keep as string */ }
  return { ok: true, isError: parsed.result?.isError === true, text, payload };
}

export interface McpV2DashboardSnapshot {
  fetchedAt: string;
  baseUrl: string | null;
  serverInfo: { name: string; version: string; description?: string } | null;
  protocolVersion: string | null;
  toolCounts: { total: number; byNamespace: Record<string, number> };
  projectCurrentState: { ok: true; payload: unknown } | { ok: false; message: string };
  projectOperatingRules: { ok: true; payload: unknown } | { ok: false; message: string };
  projectOverview: { ok: true; payload: unknown } | { ok: false; message: string };
  projectWorkStatus: { ok: true; payload: unknown } | { ok: false; message: string };
  laneOverview: { ok: true; payload: unknown } | { ok: false; message: string };
  buildOverview: { ok: true; payload: unknown } | { ok: false; message: string };
  handoffLatest: { ok: true; payload: unknown } | { ok: false; message: string };
}

/**
 * Fetches the five Admin/Dev-relevant MCP tools in parallel. Each
 * tool result is independent — a single tool failure does not break
 * the rest of the dashboard.
 */
export async function fetchMcpV2DashboardSnapshot(signal?: AbortSignal): Promise<McpV2DashboardSnapshot | null> {
  const baseUrl = v2BaseUrl();
  if (!baseUrl) {
    return {
      fetchedAt: new Date().toISOString(),
      baseUrl: null,
      serverInfo: null,
      protocolVersion: null,
      toolCounts: { total: 0, byNamespace: {} },
      projectCurrentState: { ok: false, message: 'EXPO_PUBLIC_MCP_BASE_URL not set' },
      projectOperatingRules: { ok: false, message: 'EXPO_PUBLIC_MCP_BASE_URL not set' },
      projectOverview: { ok: false, message: 'EXPO_PUBLIC_MCP_BASE_URL not set' },
      projectWorkStatus: { ok: false, message: 'EXPO_PUBLIC_MCP_BASE_URL not set' },
      laneOverview: { ok: false, message: 'EXPO_PUBLIC_MCP_BASE_URL not set' },
      buildOverview: { ok: false, message: 'EXPO_PUBLIC_MCP_BASE_URL not set' },
      handoffLatest: { ok: false, message: 'EXPO_PUBLIC_MCP_BASE_URL not set' },
    };
  }

  const initialised = await mcpV2InitializeAndListTools(signal);
  if (!initialised.ok) {
    return {
      fetchedAt: new Date().toISOString(),
      baseUrl,
      serverInfo: null,
      protocolVersion: null,
      toolCounts: { total: 0, byNamespace: {} },
      projectCurrentState: { ok: false, message: initialised.message },
      projectOperatingRules: { ok: false, message: initialised.message },
      projectOverview: { ok: false, message: initialised.message },
      projectWorkStatus: { ok: false, message: initialised.message },
      laneOverview: { ok: false, message: initialised.message },
      buildOverview: { ok: false, message: initialised.message },
      handoffLatest: { ok: false, message: initialised.message },
    };
  }

  const byNamespace: Record<string, number> = {};
  for (const t of initialised.tools) {
    const ns = t.name.split('.')[0] ?? 'unknown';
    byNamespace[ns] = (byNamespace[ns] ?? 0) + 1;
  }

  const results = await Promise.all([
    mcpV2CallTool('project.get_current_state', {}, signal),
    mcpV2CallTool('project.get_operating_rules', {}, signal),
    mcpV2CallTool('project.get_overview', {}, signal),
    mcpV2CallTool('project.get_work_status', {}, signal),
    mcpV2CallTool('mobile.get_lane_overview', {}, signal),
    mcpV2CallTool('mobile.get_build_overview', {}, signal),
    mcpV2CallTool('handoff.get_latest', {}, signal),
  ]);
  const [current, rules, proj, work, lane, build, handoff] = results;

  const wrap = (r: McpV2CallResult): { ok: true; payload: unknown } | { ok: false; message: string } =>
    r.ok ? { ok: true, payload: r.payload } : { ok: false, message: r.message };

  return {
    fetchedAt: new Date().toISOString(),
    baseUrl,
    serverInfo: initialised.serverInfo,
    protocolVersion: initialised.protocolVersion,
    toolCounts: { total: initialised.tools.length, byNamespace },
    projectCurrentState: wrap(current),
    projectOperatingRules: wrap(rules),
    projectOverview: wrap(proj),
    projectWorkStatus: wrap(work),
    laneOverview: wrap(lane),
    buildOverview: wrap(build),
    handoffLatest: wrap(handoff),
  };
}
