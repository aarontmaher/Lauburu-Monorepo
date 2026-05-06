/**
 * Unified MCP v2 endpoint — POST /mcp/v2.
 *
 * Implements Phase 1 of docs/UNIFIED_MCP_PLAN.md. Additive: every
 * existing endpoint (/mcp, /mcp/public, /api/*, the website MCP at
 * mcp.lauburugrapplingmap.com/mcp) keeps working unchanged. This
 * file is the new namespaced surface, NOT a replacement.
 *
 * Namespaces:
 *   project.*       — composed cross-project aggregates (No Auth).
 *   mobile.*_overview — counts only (No Auth).
 *   mobile.get_<full> — full /api/* payloads (admin token).
 *   integrations.get_overview — provider counts (No Auth).
 *   handoff.*       — composed handoff feed across both projects.
 *   website.*       — JSON-RPC proxy to mcp.lauburugrapplingmap.com/mcp.
 *
 * Auth: Authorization: Bearer <ATHLETE_MEMORY_API_TOKEN> OR
 *       x-athlete-memory-token: <token>. Public-safe tools never
 *       check auth; admin tools fail-soft with an isError content
 *       block when the token is missing.
 */

import type { Env } from './worker-env';
import { getSupabaseAdapter } from './supabase';
import { buildControlCentreSnapshot } from './control-centre';

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
  name: 'lauburu-mcp-unified',
  version: '0.1.0',
  description:
    'Unified Lauburu / GrapplingMap MCP. Namespaced tools across project / mobile / website / integrations / handoff. Public-safe tools No Auth; admin tools require ATHLETE_MEMORY_API_TOKEN.',
};

const WEBSITE_MCP_URL = 'https://mcp.lauburugrapplingmap.com/mcp';

// ── transport (matches mcp-public.ts content negotiation) ─────────────

function rpcResult(id: JsonRpcResponse['id'], result: unknown): JsonRpcResponse {
  return { jsonrpc: '2.0', id, result };
}
function rpcError(id: JsonRpcResponse['id'], code: number, message: string): JsonRpcResponse {
  return { jsonrpc: '2.0', id, error: { code, message } };
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
  return clientWantsSse(request) ? sseResponse(body, init) : jsonResponse(body, init);
}

function presentedToken(request: Request): string {
  const custom = request.headers.get('x-athlete-memory-token') ?? '';
  if (custom) return custom;
  const auth = request.headers.get('Authorization') ?? request.headers.get('authorization') ?? '';
  const match = auth.match(/^Bearer\s+(.+)$/i);
  return match?.[1] ?? '';
}
function tokenAuthorised(request: Request, env: Env): boolean {
  const expected = env.ATHLETE_MEMORY_API_TOKEN ?? '';
  if (!expected) return false;
  return presentedToken(request) === expected;
}

function adminGateError(): unknown {
  return {
    content: [{
      type: 'text',
      text: 'admin token required for this tool. The public-safe equivalent (project.get_overview / mobile.get_*_overview / website.* / integrations.get_overview) is callable without auth.',
    }],
    isError: true,
  };
}

// ── tool implementations: project.* ───────────────────────────────────

async function buildProjectOverview(env: Env): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);

  let mobileTopPriority: { source: 'mobile'; title: string; status: string } | null = null;
  let openManualStepsCount = 0;

  if (adapter.configured) {
    const work = await adapter.fetchSingleRowPayload('connector_work_status') as {
      currentPriority?: string;
    } | null;
    if (work?.currentPriority) {
      mobileTopPriority = {
        source: 'mobile',
        title: String(work.currentPriority).slice(0, 120),
        status: 'live',
      };
    }
    const top = await adapter.fetchTopBacklogItem();
    if (top && !mobileTopPriority) {
      mobileTopPriority = {
        source: 'mobile',
        title: top.title.slice(0, 120),
        status: top.status,
      };
    }
    const manual = await adapter.fetchManualSteps(50);
    if (manual) {
      openManualStepsCount = manual.filter((m) => m.approval === 'pending').length;
    }
  }

  const websitePendingCount = await proxyWebsiteCount();

  return {
    schemaVersion: 1,
    generatedAt,
    mobileTopPriority,
    openManualStepsCount,
    websitePendingCount,
    publicSafe: true,
  };
}

async function buildProjectListPriorities(env: Env): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  const items: Array<{ source: 'mobile'; rank: number; title: string; status: string }> = [];
  if (adapter.configured) {
    const top = await adapter.fetchTopBacklogItem();
    if (top) {
      items.push({
        source: 'mobile',
        rank: top.priority,
        title: top.title.slice(0, 120),
        status: top.status,
      });
    }
  }
  return { schemaVersion: 1, generatedAt, items, publicSafe: true };
}

async function proxyWebsiteCount(): Promise<number | null> {
  try {
    const list = await proxyWebsiteCall('list_pending_suggestions', {});
    if (Array.isArray(list)) return list.length;
    if (list && typeof list === 'object' && 'count' in (list as object)) {
      const c = (list as { count?: unknown }).count;
      if (typeof c === 'number') return c;
    }
    return null;
  } catch {
    return null;
  }
}

// ── mobile.* (overview = No Auth, full = admin token) ─────────────────

async function buildMobileLaneOverview(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const generatedAt = new Date().toISOString();
  if (!adapter.configured) return { totalLanes: 0, byStatus: emptyLaneStatusCounts(), publicPreview: true, generatedAt };
  const rows = await adapter.fetchCoderLaneRows();
  if (!rows) return { totalLanes: 0, byStatus: emptyLaneStatusCounts(), publicPreview: true, generatedAt };
  const byStatus = emptyLaneStatusCounts();
  for (const row of rows) {
    const p = row.payload as { status?: string };
    const s = (p.status as keyof typeof byStatus | undefined);
    if (s && s in byStatus) byStatus[s] += 1;
  }
  return { totalLanes: rows.length, byStatus, publicPreview: true, generatedAt };
}
function emptyLaneStatusCounts() {
  return { idle: 0, working: 0, blocked: 0, needs_user: 0, needs_review: 0, done: 0 };
}

async function buildMobileBuildOverview(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const generatedAt = new Date().toISOString();
  if (!adapter.configured) return { android: null, ios: null, publicPreview: true, generatedAt };
  const payload = (await adapter.fetchSingleRowPayload('connector_build_status')) as {
    android?: { versionCode?: number | null; githubStatus?: string | null; playStatus?: string | null; playTrack?: string | null };
    ios?: { buildNumber?: string | null; githubStatus?: string | null; testflightStatus?: string | null };
  } | null;
  const android = payload?.android ?? {};
  const ios = payload?.ios ?? {};
  return {
    android: {
      versionCode: typeof android.versionCode === 'number' ? android.versionCode : null,
      githubStatus: typeof android.githubStatus === 'string' ? android.githubStatus : null,
      playStatus: typeof android.playStatus === 'string' ? android.playStatus : null,
      playTrack: typeof android.playTrack === 'string' ? android.playTrack : null,
    },
    ios: {
      buildNumber: typeof ios.buildNumber === 'string' ? ios.buildNumber : null,
      githubStatus: typeof ios.githubStatus === 'string' ? ios.githubStatus : null,
      testflightStatus: typeof ios.testflightStatus === 'string' ? ios.testflightStatus : null,
    },
    publicPreview: true,
    generatedAt,
  };
}

async function buildMobileRepoOverview(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const generatedAt = new Date().toISOString();
  if (!adapter.configured) return { branch: null, shortHead: null, publicPreview: true, generatedAt };
  const payload = (await adapter.fetchSingleRowPayload('connector_work_status')) as {
    repoStatus?: { branch?: string; head?: string };
  } | null;
  const repo = payload?.repoStatus ?? {};
  const branch = typeof repo.branch === 'string' && /^[A-Za-z0-9._\-/]{1,80}$/.test(repo.branch) ? repo.branch : null;
  const head = typeof repo.head === 'string' && /^[0-9a-f]{7,12}$/.test(repo.head) ? repo.head : null;
  return { branch, shortHead: head, publicPreview: true, generatedAt };
}

// ── integrations.* (No Auth aggregate only) ───────────────────────────

async function buildIntegrationsOverview(env: Env): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  return {
    schemaVersion: 1,
    generatedAt,
    sources: {
      apple_health: { exposure: 'ios-only', userVisible: true },
      health_connect: { exposure: 'android-only', userVisible: true },
      whoop_oauth: { exposure: 'optional', userVisible: true },
      polar_oauth: { exposure: 'optional', userVisible: true },
    },
    note: 'Per-user counts and last-sync timestamps require admin token; not exposed here.',
    publicPreview: true,
    // env presence reference so callers can sense the deployment shape
    workerSupabaseConfigured: getSupabaseAdapter(env).configured === true,
  };
}

// ── handoff.* (composed across mobile + website) ──────────────────────

async function buildHandoffLatest(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const generatedAt = new Date().toISOString();
  const entries: Array<{ source: 'mobile' | 'website'; generatedAt: string | null; summary: string; manualStepsCount: number | null }> = [];

  if (adapter.configured) {
    const payload = await adapter.fetchSingleRowPayload('connector_handoff') as {
      generatedAt?: string;
      latestClaudePrompt?: string | null;
      latestCodexPrompt?: string | null;
      manualSteps?: unknown[];
    } | null;
    if (payload) {
      entries.push({
        source: 'mobile',
        generatedAt: typeof payload.generatedAt === 'string' ? payload.generatedAt : null,
        summary: `mobile bridge handoff — claude=${payload.latestClaudePrompt ?? '—'} codex=${payload.latestCodexPrompt ?? '—'}`.slice(0, 200),
        manualStepsCount: Array.isArray(payload.manualSteps) ? payload.manualSteps.length : null,
      });
    }
  }

  const websiteHandoff = await proxyWebsiteCall('get_handoff', {}).catch(() => null);
  if (websiteHandoff) {
    entries.push({
      source: 'website',
      generatedAt: pickWebsiteHandoffTime(websiteHandoff),
      summary: pickWebsiteHandoffSummary(websiteHandoff),
      manualStepsCount: null,
    });
  }

  entries.sort((a, b) => (b.generatedAt ?? '').localeCompare(a.generatedAt ?? ''));
  return { schemaVersion: 1, generatedAt, entries, publicPreview: true };
}
function pickWebsiteHandoffTime(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') return null;
  const candidates = ['generated_at', 'generatedAt', 'created_at', 'createdAt', 'updated_at', 'updatedAt'];
  for (const k of candidates) {
    const v = (payload as Record<string, unknown>)[k];
    if (typeof v === 'string') return v;
  }
  return null;
}
function pickWebsiteHandoffSummary(payload: unknown): string {
  if (!payload || typeof payload !== 'object') return 'website handoff (shape unknown)';
  const candidates = ['summary', 'description', 'instructions', 'title'];
  for (const k of candidates) {
    const v = (payload as Record<string, unknown>)[k];
    if (typeof v === 'string') return v.slice(0, 200);
  }
  return 'website handoff';
}

// ── mobile.* admin (delegate to existing /api/* shapes) ───────────────

async function buildMobileControlCentre(env: Env): Promise<unknown> {
  return buildControlCentreSnapshot(env);
}
async function buildMobileFullSingle(env: Env, table: string): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) return { error: 'supabase not configured' };
  return (await adapter.fetchSingleRowPayload(table)) ?? null;
}
async function buildMobileCoderLanes(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) return { lanes: [] };
  const rows = await adapter.fetchCoderLaneRows();
  return { schemaVersion: 1, generatedAt: new Date().toISOString(), lanes: (rows ?? []).map((r) => r.payload) };
}
async function buildMobileTerminalSummary(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) return { entries: [] };
  const entries = await adapter.fetchTerminalEntries(50);
  return { schemaVersion: 1, generatedAt: new Date().toISOString(), entries: entries ?? [] };
}

// ── website.* proxy ──────────────────────────────────────────────────

interface ProxyHandshake {
  sessionId: string;
  protocolVersion: string;
}

async function proxyHandshake(): Promise<ProxyHandshake | null> {
  try {
    const initRes = await fetch(WEBSITE_MCP_URL, {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream, application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2025-03-26',
          capabilities: {},
          clientInfo: { name: 'lauburu-mcp-v2-proxy', version: '0.1.0' },
        },
      }),
    });
    const sessionId = initRes.headers.get('mcp-session-id') ?? initRes.headers.get('Mcp-Session-Id');
    if (!sessionId) return null;
    // notifications/initialized — no response body required.
    await fetch(WEBSITE_MCP_URL, {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream, application/json',
        'Content-Type': 'application/json',
        'Mcp-Session-Id': sessionId,
      },
      body: JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }),
    });
    return { sessionId, protocolVersion: '2025-03-26' };
  } catch {
    return null;
  }
}

async function proxyWebsiteCall(name: string, args: unknown): Promise<unknown> {
  const handshake = await proxyHandshake();
  if (!handshake) throw new Error('proxy_unavailable');
  const callRes = await fetch(WEBSITE_MCP_URL, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream, application/json',
      'Content-Type': 'application/json',
      'Mcp-Session-Id': handshake.sessionId,
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/call',
      params: { name, arguments: args ?? {} },
    }),
  });
  const text = await callRes.text();
  // Response is SSE-framed: `event: message\ndata: <json>\n\n`.
  const match = text.match(/data:\s*(\{[\s\S]*?\})\s*$/m);
  if (!match) return null;
  const parsed = JSON.parse(match[1]) as { result?: { content?: Array<{ text?: string }> } };
  const innerText = parsed.result?.content?.[0]?.text ?? '';
  if (!innerText) return null;
  try { return JSON.parse(innerText); } catch { return innerText; }
}

async function proxyWebsiteToolsList(): Promise<Array<{ name: string; description: string; inputSchema: unknown }>> {
  try {
    const handshake = await proxyHandshake();
    if (!handshake) return [];
    const res = await fetch(WEBSITE_MCP_URL, {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream, application/json',
        'Content-Type': 'application/json',
        'Mcp-Session-Id': handshake.sessionId,
      },
      body: JSON.stringify({ jsonrpc: '2.0', id: 3, method: 'tools/list' }),
    });
    const text = await res.text();
    const match = text.match(/data:\s*(\{[\s\S]*?\})\s*$/m);
    if (!match) return [];
    const parsed = JSON.parse(match[1]) as { result?: { tools?: Array<{ name: string; description?: string; inputSchema?: unknown }> } };
    const tools = parsed.result?.tools ?? [];
    return tools.map((t) => ({
      name: `website.${t.name}`,
      description: `[proxy] ${t.description ?? ''}`,
      inputSchema: t.inputSchema ?? { type: 'object', properties: {}, required: [] },
    }));
  } catch {
    return [];
  }
}

// ── tool registry ────────────────────────────────────────────────────

interface LocalToolEntry {
  name: string;
  description: string;
  inputSchema: { type: 'object'; properties: Record<string, never>; required: string[] };
  auth: 'public' | 'admin';
  build: (env: Env) => Promise<unknown>;
}

const LOCAL_TOOLS: readonly LocalToolEntry[] = [
  {
    name: 'project.get_overview',
    description: 'Cross-project aggregate: top mobile priority, open manual-steps count, website pending suggestions count. No free text > 120 chars. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildProjectOverview,
  },
  {
    name: 'project.list_priorities',
    description: 'Top backlog items across the active mobile-app project. Each entry: source / rank / title / status. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildProjectListPriorities,
  },
  {
    name: 'mobile.get_lane_overview',
    description: 'Coder lane counts by status enum. No per-lane text. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildMobileLaneOverview,
  },
  {
    name: 'mobile.get_build_overview',
    description: 'Latest paired-build status enums + Android versionCode + iOS buildNumber. No EAS / submission UUIDs. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildMobileBuildOverview,
  },
  {
    name: 'mobile.get_repo_overview',
    description: 'Branch + short HEAD SHA. Both already public on GitHub. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildMobileRepoOverview,
  },
  {
    name: 'mobile.get_control_centre',
    description: 'Full ControlCentreSnapshot (priority, blocker, lanes, build, repo, manualSteps, topBacklog, suggestionCounts, promptLibrary, safety). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    build: buildMobileControlCentre,
  },
  {
    name: 'mobile.get_coder_lanes',
    description: 'Full coder-lanes payload — per-lane summaries with text, prompts, dirtyFiles. Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    build: buildMobileCoderLanes,
  },
  {
    name: 'mobile.get_work_status',
    description: 'Full WorkStatus payload (priority, blocker, liveStatus, repoStatus, nextAction). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    build: (env) => buildMobileFullSingle(env, 'connector_work_status'),
  },
  {
    name: 'mobile.get_build_status',
    description: 'Full BuildStatus payload (Android + iOS release rows including IDs). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    build: (env) => buildMobileFullSingle(env, 'connector_build_status'),
  },
  {
    name: 'mobile.get_handoff',
    description: 'Full Handoff payload (manualSteps text, doNotTouch, safeToBuild). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    build: (env) => buildMobileFullSingle(env, 'connector_handoff'),
  },
  {
    name: 'mobile.get_terminal_summary',
    description: 'TerminalSummary entries (≤50, most recent first, full text). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    build: buildMobileTerminalSummary,
  },
  {
    name: 'integrations.get_overview',
    description: 'Per-platform exposure of Apple Health (iOS only) / Health Connect (Android only) / WHOOP / Polar. Aggregates only. No per-user data. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildIntegrationsOverview,
  },
  {
    name: 'handoff.get_latest',
    description: 'Latest handoff entries from both projects, each tagged source: mobile|website. Public-safe summary; admin token unlocks richer fields.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildHandoffLatest,
  },
];

const LOCAL_BY_NAME = new Map(LOCAL_TOOLS.map((t) => [t.name, t] as const));

// ── JSON-RPC dispatch ────────────────────────────────────────────────

async function listAllTools(): Promise<Array<{ name: string; description: string; inputSchema: unknown }>> {
  const local = LOCAL_TOOLS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema }));
  const website = await proxyWebsiteToolsList();
  return [...local, ...website];
}

async function dispatchToolCall(env: Env, request: Request, name: string, args: unknown): Promise<unknown> {
  if (name.startsWith('website.')) {
    const upstream = name.slice('website.'.length);
    try {
      const payload = await proxyWebsiteCall(upstream, args ?? {});
      return {
        content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
        isError: false,
      };
    } catch {
      return {
        content: [{ type: 'text', text: 'proxy_unavailable: website MCP unreachable. Try again later.' }],
        isError: true,
      };
    }
  }
  const tool = LOCAL_BY_NAME.get(name);
  if (!tool) return null;
  if (tool.auth === 'admin' && !tokenAuthorised(request, env)) {
    return adminGateError();
  }
  const payload = await tool.build(env);
  return {
    content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
    isError: false,
  };
}

async function handleRpcRequest(req: JsonRpcRequest, env: Env, request: Request): Promise<JsonRpcResponse | null> {
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
          'Unified Lauburu / GrapplingMap MCP. Public-safe tools (project.* / *.get_*_overview / website.* / integrations.get_overview / handoff.*) work without auth. Admin tools (mobile.get_<full>) require x-athlete-memory-token or Authorization: Bearer. Detail in docs/UNIFIED_MCP_PLAN.md.',
      });
    case 'notifications/initialized':
    case 'notifications/cancelled':
    case 'notifications/progress':
      return null;
    case 'ping':
      return rpcResult(id, {});
    case 'tools/list': {
      const tools = await listAllTools();
      return rpcResult(id, { tools });
    }
    case 'tools/call': {
      const params = (req.params as { name?: string; arguments?: unknown }) ?? {};
      const name = params.name ?? '';
      const result = await dispatchToolCall(env, request, name, params.arguments);
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

export async function handleMcpV2(request: Request, env: Env): Promise<Response> {
  if (request.method === 'GET') {
    const tools = await listAllTools();
    return jsonResponse({
      ok: true,
      protocolVersion: PROTOCOL_VERSION,
      serverInfo: SERVER_INFO,
      transport: 'streamable-http',
      auth: {
        public: 'no auth required for public-safe tools',
        admin: 'Authorization: Bearer <ATHLETE_MEMORY_API_TOKEN> OR x-athlete-memory-token header',
      },
      tools: tools.map((t) => ({ name: t.name, description: (t.description ?? '').slice(0, 160) })),
      hint: 'POST JSON-RPC 2.0 here. See docs/UNIFIED_MCP_PLAN.md for namespace conventions.',
    });
  }

  if (request.method !== 'POST') {
    return jsonResponse(rpcError(null, -32600, 'POST or GET only.'), { status: 405, headers: { allow: 'GET, POST' } });
  }

  let body: unknown;
  try { body = await request.json(); } catch { return jsonResponse(rpcError(null, -32700, 'Parse error'), { status: 400 }); }

  if (Array.isArray(body)) {
    const responses = await Promise.all(body.map((req) => handleRpcRequest(req as JsonRpcRequest, env, request)));
    const filtered = responses.filter((r): r is JsonRpcResponse => r !== null);
    if (filtered.length === 0) return new Response(null, { status: 202 });
    return negotiated(request, filtered);
  }
  const response = await handleRpcRequest(body as JsonRpcRequest, env, request);
  if (response === null) return new Response(null, { status: 202 });
  return negotiated(request, response);
}
