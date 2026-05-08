/**
 * /mcp/core — compact public-safe MCP surface for ChatGPT.
 *
 * Why this exists: ChatGPT's custom MCP connector creation flow
 * fails on /mcp/v2 because that endpoint advertises ~49 tools
 * (including 22 website-proxy tools with verbose Pydantic-style
 * schemas). Smaller MCP surfaces — see WHOOP — connect cleanly.
 * /mcp/core trims the public-safe surface to the 6 tools that
 * matter for cross-project visibility, so ChatGPT can attach
 * without timing out or hitting an internal tool/schema cap.
 *
 * Behaviour: identical Streamable HTTP / JSON-RPC contract as
 * /mcp/v2 — protocolVersion 2025-03-26, OPTIONS preflight, GET
 * descriptor, POST JSON-RPC, content negotiation between
 * application/json and text/event-stream. All 6 tools are
 * public-safe (No Auth required).
 *
 * Tool builders are imported from ./mcp-v2 so behaviour cannot
 * drift between the two surfaces — /mcp/core is a strict subset
 * view of /mcp/v2.
 */

import type { Env } from './worker-env';
import { buildOperatingRulesPayload } from './operating-rules';
import {
  buildProjectCurrentState,
  buildHandoffLatest,
  buildIntegrationsOverview,
  buildMobileLaneOverview,
  buildMobileBuildOverview,
} from './mcp-v2';

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
const SERVER_INFO = {
  name: 'lauburu-mcp-core',
  version: '0.1.0',
  description:
    'Compact public-safe Lauburu / GrapplingMap MCP. Six tools, No Auth, Streamable HTTP. Designed for ChatGPT custom MCP connectors that fail on the larger /mcp/v2.',
};

interface CoreTool {
  name: string;
  description: string;
  inputSchema: { type: 'object'; properties: Record<string, unknown>; required: string[] };
  build: (env: Env) => Promise<unknown>;
}

const CORE_TOOLS: readonly CoreTool[] = [
  {
    name: 'project.get_current_state',
    description:
      'Canonical "what is the team working on right now" snapshot. Composes priority / blocker / next action + per-lane (claude / codex) status + sanitised task summaries (≤140 char) + Android v + iOS Build state + freshness flag. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    build: buildProjectCurrentState,
  },
  {
    name: 'project.get_operating_rules',
    description:
      'Canonical 18 operating rules every coder / agent / consumer must follow. Stable rule IDs 1..18 + titles + bodies. Mirror of docs/OPERATING_RULES.md. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    build: async () => buildOperatingRulesPayload(),
  },
  {
    name: 'handoff.get_latest',
    description:
      'Latest handoff entries from both projects, each tagged source: mobile|website. Public-safe summary; admin token unlocks richer fields on /mcp/v2.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    build: buildHandoffLatest,
  },
  {
    name: 'integrations.get_overview',
    description:
      'Per-platform exposure of Apple Health (iOS only) / Health Connect (Android only) / WHOOP / Polar. Aggregates only. No per-user data. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    build: buildIntegrationsOverview,
  },
  {
    name: 'mobile.get_lane_overview',
    description: 'Coder lane counts by status enum. No per-lane text. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    build: buildMobileLaneOverview,
  },
  {
    name: 'mobile.get_build_overview',
    description:
      'Latest paired-build status enums + Android versionCode + iOS buildNumber. No EAS / submission UUIDs. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    build: buildMobileBuildOverview,
  },
];

const CORE_BY_NAME = new Map(CORE_TOOLS.map((t) => [t.name, t] as const));

// ── transport helpers (mirror mcp-v2.ts; intentionally duplicated to keep this surface independently testable) ──

function rpcResult(id: JsonRpcResponse['id'], result: unknown): JsonRpcResponse {
  return { jsonrpc: '2.0', id, result };
}
function rpcError(id: JsonRpcResponse['id'], code: number, message: string): JsonRpcResponse {
  return { jsonrpc: '2.0', id, error: { code, message } };
}
function corsHeaders(): Record<string, string> {
  return {
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'GET, POST, OPTIONS',
    'access-control-allow-headers': 'authorization, content-type, mcp-session-id',
    'access-control-expose-headers': 'content-type, mcp-session-id',
  };
}
function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      'content-type': 'application/json',
      'cache-control': 'no-store',
      ...corsHeaders(),
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
      ...corsHeaders(),
      ...(init.headers ?? {}),
    },
  });
}
function clientWantsSse(request: Request): boolean {
  const accept = request.headers.get('accept') ?? request.headers.get('Accept') ?? '';
  return /text\/event-stream/i.test(accept);
}
function negotiated(request: Request, body: unknown, init: ResponseInit = {}): Response {
  return clientWantsSse(request) ? sseResponse(body, init) : jsonResponse(body, init);
}

async function dispatchToolCall(env: Env, name: string, _args: unknown): Promise<unknown> {
  const tool = CORE_BY_NAME.get(name);
  if (!tool) return null;
  const payload = await tool.build(env);
  return {
    content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
    isError: false,
  };
}

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
          'Compact Lauburu / GrapplingMap MCP — six public-safe tools for cross-project visibility. No auth required. For the full ~49-tool surface (admin tools, website proxy, QA, release gate detail), use /mcp/v2.',
      });
    case 'notifications/initialized':
    case 'notifications/cancelled':
    case 'notifications/progress':
      return null;
    case 'ping':
      return rpcResult(id, {});
    case 'tools/list':
      return rpcResult(id, {
        tools: CORE_TOOLS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })),
      });
    case 'tools/call': {
      const params = (req.params as { name?: string; arguments?: unknown }) ?? {};
      const name = params.name ?? '';
      const result = await dispatchToolCall(env, name, params.arguments);
      if (result === null) return rpcError(id, -32602, `Unknown tool: ${name || '<missing>'}`);
      return rpcResult(id, result);
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

export async function handleMcpCore(request: Request, env: Env): Promise<Response> {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (request.method === 'GET') {
    return jsonResponse({
      ok: true,
      protocolVersion: PROTOCOL_VERSION,
      serverInfo: SERVER_INFO,
      transport: 'streamable-http',
      auth: { public: 'no auth required for any tool on this surface' },
      tools: CORE_TOOLS.map((t) => ({ name: t.name, description: t.description.slice(0, 160) })),
      hint: 'POST JSON-RPC 2.0 here. Six public-safe tools only — for the full surface, use /mcp/v2.',
    });
  }
  if (request.method !== 'POST') {
    return jsonResponse(rpcError(null, -32600, 'POST or GET only.'), { status: 405, headers: { allow: 'GET, POST, OPTIONS' } });
  }

  let body: unknown;
  try { body = await request.json(); } catch { return jsonResponse(rpcError(null, -32700, 'Parse error'), { status: 400 }); }

  if (Array.isArray(body)) {
    const responses = await Promise.all(body.map((req) => handleRpcRequest(req as JsonRpcRequest, env)));
    const filtered = responses.filter((r): r is JsonRpcResponse => r !== null);
    if (filtered.length === 0) return new Response(null, { status: 202, headers: corsHeaders() });
    return negotiated(request, filtered);
  }
  const response = await handleRpcRequest(body as JsonRpcRequest, env);
  if (response === null) return new Response(null, { status: 202, headers: corsHeaders() });
  return negotiated(request, response);
}
