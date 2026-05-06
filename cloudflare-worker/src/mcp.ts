/**
 * Minimal Streamable-HTTP MCP server for the Lauburu connector.
 *
 * Speaks JSON-RPC 2.0 over HTTP `POST /mcp`. Returns plain
 * `application/json` (no SSE for now — the spec allows non-streaming
 * fallback for clients that don't request `text/event-stream`).
 *
 * Read-only by design. The five tools below are thin proxies over the
 * same Supabase fetch helpers + placeholder fallbacks the REST routes
 * use, so MCP clients see exactly what `GET /api/<name>` would return.
 *
 * Auth: the same admin token the REST routes accept. The MCP endpoint
 * accepts EITHER:
 *   - `x-athlete-memory-token: <token>`   (existing custom header)
 *   - `Authorization: Bearer <token>`     (MCP-standard form)
 * so ChatGPT / Claude.ai connector UIs can use whichever they support.
 */

import type { Env } from './worker-env';
import { getSupabaseAdapter, type ConnectorRouteKey } from './supabase';

interface JsonRpcRequest {
  jsonrpc?: string;
  id?: string | number | null;
  method?: string;
  params?: unknown;
}

interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: string | number | null;
  result?: unknown;
  error?: { code: number; message: string; data?: unknown };
}

const PROTOCOL_VERSION = '2025-03-26';
const SERVER_INFO = { name: 'lauburu-mcp', version: '0.1.0' };

const TOOLS = [
  {
    name: 'get_work_status',
    description:
      'Returns the connector work_status payload — current priority, current blocker, live mobile build state, repo state, and next action. Read-only; admin-token gated.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
  {
    name: 'get_coder_lanes',
    description:
      'Returns one CoderLaneRow per active lane (claude, codex, etc) with status, lastSeenAt, currentPromptId, lastPromptId, lastSummary (≤1200 chars, redacted), lastCommit, dirtyFiles, nextPrompt. Read-only.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
  {
    name: 'get_build_status',
    description:
      'Returns the latest paired build snapshot — Android (versionCode, GitHub run id, EAS build id, Play submission id, Play status, Play track) plus iOS (buildNumber, GitHub run id, EAS build id, TestFlight submission id, TestFlight status, group). Read-only.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
  {
    name: 'get_handoff',
    description:
      'Returns the most recent owner-set handoff — latestClaudePrompt, latestCodexPrompt, manualSteps, doNotTouch, safeToBuild flag, safeToBuildReason. Read-only.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
  {
    name: 'get_terminal_summary',
    description:
      'Returns the most recent terminal summary log entries (≤50, most recent first). Each entry: laneId, at, summary (≤1200), verification (≤240), nextAction (≤240), exitCode. Sourced from mark-agent-done writes via the bridge. Read-only.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
] as const;

type ToolName = (typeof TOOLS)[number]['name'];

function rpcResult(id: JsonRpcResponse['id'], result: unknown): JsonRpcResponse {
  return { jsonrpc: '2.0', id, result };
}

function rpcError(id: JsonRpcResponse['id'], code: number, message: string, data?: unknown): JsonRpcResponse {
  return { jsonrpc: '2.0', id, error: { code, message, ...(data !== undefined ? { data } : {}) } };
}

function presentedToken(request: Request): string {
  const custom = request.headers.get('x-athlete-memory-token') ?? '';
  if (custom) return custom;
  const auth = request.headers.get('Authorization') ?? request.headers.get('authorization') ?? '';
  const match = auth.match(/^Bearer\s+(.+)$/i);
  return match?.[1] ?? '';
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      'content-type': 'application/json',
      'cache-control': 'no-store',
      ...(init.headers ?? {}),
    },
  });
}

function sseResponse(body: unknown, init: ResponseInit = {}): Response {
  const frame = `event: message\ndata: ${JSON.stringify(body)}\n\n`;
  return new Response(frame, {
    ...init,
    headers: {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache, no-transform',
      ...(init.headers ?? {}),
    },
  });
}

function clientWantsSse(request: Request): boolean {
  const accept = request.headers.get('accept') ?? request.headers.get('Accept') ?? '';
  return /text\/event-stream/i.test(accept);
}

function negotiated(request: Request, body: unknown, init: ResponseInit = {}): Response {
  return clientWantsSse(request)
    ? sseResponse(body, init)
    : jsonResponse(body, init);
}

async function fetchSinglePayload(env: Env, table: string): Promise<unknown | null> {
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) return null;
  return adapter.fetchSingleRowPayload(table);
}

async function buildToolPayload(env: Env, route: ConnectorRouteKey, name: ToolName): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const supabaseConfigured = adapter.configured === true;

  switch (name) {
    case 'get_work_status': {
      const payload = await fetchSinglePayload(env, 'connector_work_status');
      return payload ?? { dataSource: { source: 'placeholder' as const, reason: supabaseConfigured ? 'table_empty' : 'env_missing' } };
    }
    case 'get_coder_lanes': {
      if (adapter.configured) {
        const rows = await adapter.fetchCoderLaneRows();
        if (rows && rows.length > 0) {
          return {
            schemaVersion: 1,
            generatedAt: new Date().toISOString(),
            dataSource: { source: 'supabase' as const, table: 'connector_coder_lanes' },
            lanes: rows.map((r) => r.payload),
          };
        }
      }
      return { dataSource: { source: 'placeholder' as const, reason: supabaseConfigured ? 'table_empty' : 'env_missing' }, lanes: [] };
    }
    case 'get_build_status': {
      const payload = await fetchSinglePayload(env, 'connector_build_status');
      return payload ?? { dataSource: { source: 'placeholder' as const, reason: supabaseConfigured ? 'table_empty' : 'env_missing' } };
    }
    case 'get_handoff': {
      const payload = await fetchSinglePayload(env, 'connector_handoff');
      return payload ?? { dataSource: { source: 'placeholder' as const, reason: supabaseConfigured ? 'table_empty' : 'env_missing' } };
    }
    case 'get_terminal_summary': {
      if (adapter.configured) {
        const entries = await adapter.fetchTerminalEntries(50);
        if (entries) {
          return {
            schemaVersion: 1,
            generatedAt: new Date().toISOString(),
            dataSource: { source: 'supabase' as const, table: 'connector_terminal_summary' },
            entries,
          };
        }
      }
      return { dataSource: { source: 'placeholder' as const, reason: supabaseConfigured ? 'table_empty' : 'env_missing' }, entries: [] };
    }
  }
  void route;
  return null;
}

const TOOL_TO_ROUTE: Record<ToolName, ConnectorRouteKey> = {
  get_work_status: 'work_status',
  get_coder_lanes: 'coder_lanes',
  get_build_status: 'build_status',
  get_handoff: 'handoff',
  get_terminal_summary: 'terminal_summary',
};

async function handleRpcRequest(req: JsonRpcRequest, env: Env): Promise<JsonRpcResponse | null> {
  if (req.jsonrpc !== '2.0') {
    return rpcError(req.id ?? null, -32600, 'Invalid Request: jsonrpc must be "2.0"');
  }
  const isNotification = req.id === undefined;
  const id = req.id ?? null;

  switch (req.method) {
    case 'initialize':
      return rpcResult(id, {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: { tools: { listChanged: false } },
        serverInfo: SERVER_INFO,
        instructions:
          'Read-only Lauburu MCP connector. Five tools surface live coder/build/handoff status. No writes, no terminal control, no secrets.',
      });

    case 'notifications/initialized':
    case 'notifications/cancelled':
    case 'notifications/progress':
      return null; // notifications carry no response

    case 'ping':
      return rpcResult(id, {});

    case 'tools/list':
      return rpcResult(id, { tools: TOOLS });

    case 'tools/call': {
      const params = (req.params as { name?: string; arguments?: unknown }) ?? {};
      const name = params.name as ToolName | undefined;
      if (!name || !(name in TOOL_TO_ROUTE)) {
        return rpcError(id, -32602, `Unknown tool: ${name ?? '<missing>'}`);
      }
      const route = TOOL_TO_ROUTE[name];
      try {
        const payload = await buildToolPayload(env, route, name);
        return rpcResult(id, {
          content: [
            { type: 'text', text: JSON.stringify(payload, null, 2) },
          ],
          isError: false,
        });
      } catch (err) {
        return rpcResult(id, {
          content: [
            { type: 'text', text: `tool error: ${err instanceof Error ? err.message : 'unknown'}` },
          ],
          isError: true,
        });
      }
    }

    case 'prompts/list':
      return rpcResult(id, { prompts: [] });

    case 'resources/list':
      return rpcResult(id, { resources: [] });

    default:
      if (isNotification) return null;
      return rpcError(id, -32601, `Method not found: ${req.method ?? '<missing>'}`);
  }
}

export async function handleMcp(request: Request, env: Env): Promise<Response> {
  // Fast-fail without a configured admin token.
  const expected = env.ATHLETE_MEMORY_API_TOKEN ?? '';
  if (!expected) {
    return jsonResponse(
      rpcError(null, -32603, 'Admin token not configured on this Worker.'),
      { status: 503 },
    );
  }

  // GET /mcp returns server metadata (helpful for debugging; no auth
  // leak since it just lists the public tool surface).
  if (request.method === 'GET') {
    return jsonResponse({
      ok: true,
      protocolVersion: PROTOCOL_VERSION,
      serverInfo: SERVER_INFO,
      transport: 'streamable-http',
      auth: {
        header: 'x-athlete-memory-token',
        alternate: 'Authorization: Bearer <token>',
      },
      tools: TOOLS.map((t) => ({ name: t.name, description: t.description })),
      hint: 'POST JSON-RPC 2.0 here to use the MCP protocol (initialize / tools/list / tools/call).',
    });
  }

  if (request.method !== 'POST') {
    return jsonResponse(
      rpcError(null, -32600, 'POST or GET only.'),
      { status: 405, headers: { allow: 'GET, POST' } },
    );
  }

  // Auth.
  if (presentedToken(request) !== expected) {
    return jsonResponse(
      rpcError(null, -32600, 'Forbidden — token missing or wrong.'),
      { status: 403 },
    );
  }

  // Parse.
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(rpcError(null, -32700, 'Parse error'), { status: 400 });
  }

  // Batch (array) — process each, drop notification responses.
  if (Array.isArray(body)) {
    const responses = await Promise.all(
      body.map((req) => handleRpcRequest(req as JsonRpcRequest, env)),
    );
    const filtered = responses.filter((r): r is JsonRpcResponse => r !== null);
    if (filtered.length === 0) return new Response(null, { status: 202 });
    return negotiated(request, filtered);
  }

  // Single request.
  const response = await handleRpcRequest(body as JsonRpcRequest, env);
  if (response === null) return new Response(null, { status: 202 }); // notification
  return negotiated(request, response);
}
