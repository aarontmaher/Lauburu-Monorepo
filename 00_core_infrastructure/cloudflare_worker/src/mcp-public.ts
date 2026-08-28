/**
 * Public-safe preview MCP server.
 *
 * Mounted at `/mcp/public`. ChatGPT's "Connectors" UI currently only
 * offers OAuth / No Auth / Mixed — no API-key / Bearer option — so the
 * full private MCP at `/mcp` (gated by ATHLETE_MEMORY_API_TOKEN) is not
 * usable directly from a ChatGPT custom connector. This endpoint
 * provides a STRICTLY-SANITIZED, NO-AUTH alternative that exposes ONLY
 * non-sensitive status overviews:
 *
 *   - Aggregate lane counts by status enum (idle / working / blocked /
 *     needs_user / needs_review / done) — never per-lane summaries,
 *     prompts, or file lists.
 *   - Build-status enums + the publicly-listed version code / build
 *     number (already visible on Play Internal Testing + TestFlight
 *     listings).
 *   - Repo branch + short HEAD SHA (already public on GitHub).
 *
 * NEVER exposed here:
 *   - lastSummary, currentPriority, currentBlocker, nextAction,
 *     manualSteps, safeToBuildReason — any free text.
 *   - currentPromptId, lastPromptId, nextPrompt — internal labels.
 *   - dirtyFiles, doNotTouch, repo paths of any kind.
 *   - handoff payloads beyond the count of manualSteps / doNotTouch.
 *   - terminal_summary entries — too much text content.
 *   - safeToBuild flag value — operational signal kept private.
 *
 * The full-fidelity private MCP stays at POST /mcp behind
 * `x-athlete-memory-token` / `Authorization: Bearer` for laptop curl
 * usage and any future ChatGPT OAuth wiring.
 */

import type { Env } from './worker-env';
import { getSupabaseAdapter } from './supabase';

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
  name: 'lauburu-mcp-public-preview',
  version: '0.1.0',
  /** Surfaces in clientInfo so callers see this is intentionally limited. */
  description:
    'Public-safe preview. Sanitized status overviews only — no free text, no paths, no prompts. Full-fidelity MCP at /mcp is admin-token-gated.',
};

const ALLOWED_LANE_STATUSES = [
  'idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done',
] as const;
type LaneStatus = (typeof ALLOWED_LANE_STATUSES)[number];

const ALLOWED_GITHUB_STATUSES = [
  'queued', 'in_progress', 'success', 'failure', 'cancelled',
] as const;
type GithubStatus = (typeof ALLOWED_GITHUB_STATUSES)[number];

const ALLOWED_PLAY_STATUSES = [
  'submitted_draft', 'submitted_completed', 'rolled_out', 'failed',
] as const;
type PlayStatus = (typeof ALLOWED_PLAY_STATUSES)[number];

const ALLOWED_TF_STATUSES = [
  'uploaded_processing', 'available', 'invalid_binary', 'failed',
] as const;
type TestflightStatus = (typeof ALLOWED_TF_STATUSES)[number];

const TOOLS = [
  {
    name: 'get_public_mcp_health',
    description:
      'Diagnostic tool. Returns tool list, server version, protocol version, generatedAt, and the data-source state (supabase | repo-only). Use this to confirm the MCP connector is wired before calling any other tool. No secrets, no paths. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
  {
    name: 'get_lane_overview',
    description:
      'Aggregate count of coder lanes (Claude, Codex, etc) grouped by status enum (idle / working / blocked / needs_user / needs_review / done). Returns counts only — no per-lane text, no prompt IDs, no file paths. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
  {
    name: 'get_build_overview',
    description:
      'Latest paired-build status enums plus the publicly-listed Android versionCode + iOS buildNumber. Includes GitHub workflow status, Play submission status, TestFlight status. No EAS build IDs, no submission UUIDs, no run IDs. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
  {
    name: 'get_repo_overview',
    description:
      'Repo branch name and the short SHA of HEAD. Both already public on GitHub. No commit messages, no dirty file counts, no untracked file counts. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] as string[] },
  },
] as const;

type ToolName = (typeof TOOLS)[number]['name'];

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

/**
 * Wraps a JSON-RPC response in a single Server-Sent Event message
 * frame. ChatGPT's MCP connector negotiates Streamable-HTTP via the
 * Accept header — when the client signals `text/event-stream`, the
 * spec lets the server return either plain JSON or an SSE stream.
 * Connectors that hard-require SSE (ChatGPT) fail the connection
 * if we return plain JSON, even though the JSON body is valid.
 *
 * Returning a single `event: message\ndata: …\n\n` frame satisfies
 * both the spec and the strict client. We do not hold the stream
 * open — one message, then close.
 */
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

// ── Strict-allowlist sanitisers ─────────────────────────────────────────
// Each sanitiser returns ONLY the named primitive fields. Everything
// else from the upstream payload is dropped. No regex on free text;
// the safe path is "build a fresh object with allow-listed scalars",
// not "filter the original".

function sanitiseLaneStatus(value: unknown): LaneStatus | null {
  if (typeof value !== 'string') return null;
  return (ALLOWED_LANE_STATUSES as readonly string[]).includes(value)
    ? (value as LaneStatus)
    : null;
}

interface LaneOverview {
  schemaVersion: 1;
  generatedAt: string;
  totalLanes: number;
  byStatus: Record<LaneStatus, number>;
  /** ISO timestamp of the most-recent lane snapshot the bridge wrote. */
  lastSnapshotAt: string | null;
  /** Always true to flag this as the public preview. */
  publicPreview: true;
}

function emptyByStatus(): Record<LaneStatus, number> {
  return {
    idle: 0, working: 0, blocked: 0,
    needs_user: 0, needs_review: 0, done: 0,
  };
}

async function buildLaneOverview(env: Env): Promise<LaneOverview> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      totalLanes: 0,
      byStatus: emptyByStatus(),
      lastSnapshotAt: null,
      publicPreview: true,
    };
  }
  const rows = await adapter.fetchCoderLaneRows();
  if (!rows) {
    return {
      schemaVersion: 1,
      generatedAt,
      totalLanes: 0,
      byStatus: emptyByStatus(),
      lastSnapshotAt: null,
      publicPreview: true,
    };
  }

  const byStatus = emptyByStatus();
  let lastSnapshotAt: string | null = null;
  for (const row of rows) {
    const payload = (row.payload ?? {}) as { status?: unknown; lastSeenAt?: unknown };
    const status = sanitiseLaneStatus(payload.status);
    if (status) byStatus[status] += 1;
    if (typeof payload.lastSeenAt === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(payload.lastSeenAt)) {
      if (!lastSnapshotAt || payload.lastSeenAt > lastSnapshotAt) {
        lastSnapshotAt = payload.lastSeenAt;
      }
    }
  }
  const totalLanes = rows.length;
  return { schemaVersion: 1, generatedAt, totalLanes, byStatus, lastSnapshotAt, publicPreview: true };
}

interface BuildOverview {
  schemaVersion: 1;
  generatedAt: string;
  android: {
    versionCode: number | null;
    githubStatus: GithubStatus | null;
    playStatus: PlayStatus | null;
    playTrack: 'internal' | 'closed' | 'open' | 'production' | null;
  };
  ios: {
    buildNumber: string | null;
    githubStatus: GithubStatus | null;
    testflightStatus: TestflightStatus | null;
  };
  publicPreview: true;
}

function pickEnum<T extends string>(value: unknown, allowed: readonly T[]): T | null {
  return typeof value === 'string' && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : null;
}

async function buildBuildOverview(env: Env): Promise<BuildOverview> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      android: { versionCode: null, githubStatus: null, playStatus: null, playTrack: null },
      ios: { buildNumber: null, githubStatus: null, testflightStatus: null },
      publicPreview: true,
    };
  }
  const payload = (await adapter.fetchSingleRowPayload('connector_build_status')) as
    | { android?: Record<string, unknown>; ios?: Record<string, unknown> }
    | null;

  const android = (payload?.android ?? {}) as Record<string, unknown>;
  const ios = (payload?.ios ?? {}) as Record<string, unknown>;
  const playTrack = pickEnum(android.playTrack, ['internal', 'closed', 'open', 'production'] as const);
  const buildNumber = typeof ios.buildNumber === 'string' && ios.buildNumber.length <= 20
    ? ios.buildNumber : null;
  const versionCode = typeof android.versionCode === 'number' && Number.isFinite(android.versionCode)
    ? android.versionCode : null;

  return {
    schemaVersion: 1,
    generatedAt,
    android: {
      versionCode,
      githubStatus: pickEnum(android.githubStatus, ALLOWED_GITHUB_STATUSES),
      playStatus: pickEnum(android.playStatus, ALLOWED_PLAY_STATUSES),
      playTrack,
    },
    ios: {
      buildNumber,
      githubStatus: pickEnum(ios.githubStatus, ALLOWED_GITHUB_STATUSES),
      testflightStatus: pickEnum(ios.testflightStatus, ALLOWED_TF_STATUSES),
    },
    publicPreview: true,
  };
}

interface RepoOverview {
  schemaVersion: 1;
  generatedAt: string;
  branch: string | null;
  lastCommitShortSha: string | null;
  publicPreview: true;
}

const SHORT_SHA_RE = /^[0-9a-f]{7,12}$/;
const BRANCH_RE = /^[A-Za-z0-9._\-/]{1,80}$/;

interface PublicMcpHealth {
  schemaVersion: 1;
  generatedAt: string;
  serverInfo: typeof SERVER_INFO;
  protocolVersion: typeof PROTOCOL_VERSION;
  /** 'supabase' when Supabase env is configured + reachable; 'repo-only' otherwise. */
  source: 'supabase' | 'repo-only';
  /** Names of every tool exposed by this public-safe endpoint. */
  toolNames: readonly string[];
  publicPreview: true;
}

async function buildPublicMcpHealth(env: Env): Promise<PublicMcpHealth> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  let source: 'supabase' | 'repo-only' = 'repo-only';
  if (adapter.configured) {
    const ping = await adapter.ping();
    if (ping.ok) source = 'supabase';
  }
  return {
    schemaVersion: 1,
    generatedAt,
    serverInfo: SERVER_INFO,
    protocolVersion: PROTOCOL_VERSION,
    source,
    toolNames: TOOLS.map((t) => t.name),
    publicPreview: true,
  };
}

async function buildRepoOverview(env: Env): Promise<RepoOverview> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) {
    return { schemaVersion: 1, generatedAt, branch: null, lastCommitShortSha: null, publicPreview: true };
  }
  const payload = (await adapter.fetchSingleRowPayload('connector_work_status')) as
    | { repoStatus?: { branch?: unknown; head?: unknown } }
    | null;

  const repo = payload?.repoStatus ?? {};
  const branch = typeof repo.branch === 'string' && BRANCH_RE.test(repo.branch) ? repo.branch : null;
  const head = typeof repo.head === 'string' && SHORT_SHA_RE.test(repo.head) ? repo.head : null;

  return { schemaVersion: 1, generatedAt, branch, lastCommitShortSha: head, publicPreview: true };
}

const TOOL_BUILDERS: Record<ToolName, (env: Env) => Promise<unknown>> = {
  get_public_mcp_health: buildPublicMcpHealth,
  get_lane_overview: buildLaneOverview,
  get_build_overview: buildBuildOverview,
  get_repo_overview: buildRepoOverview,
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
          'PUBLIC-SAFE PREVIEW. Read-only sanitized status overviews. No free text, no paths, no prompts, no terminal logs. Full-fidelity status is on a separate admin-token-gated endpoint and is NOT exposed here.',
      });

    case 'notifications/initialized':
    case 'notifications/cancelled':
    case 'notifications/progress':
      return null;

    case 'ping':
      return rpcResult(id, {});

    case 'tools/list':
      return rpcResult(id, { tools: TOOLS });

    case 'tools/call': {
      const params = (req.params as { name?: string }) ?? {};
      const name = params.name as ToolName | undefined;
      if (!name || !(name in TOOL_BUILDERS)) {
        return rpcError(id, -32602, `Unknown tool: ${name ?? '<missing>'}`);
      }
      try {
        const payload = await TOOL_BUILDERS[name](env);
        return rpcResult(id, {
          content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
          isError: false,
        });
      } catch {
        return rpcResult(id, {
          content: [{ type: 'text', text: 'tool error' }],
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

export async function handleMcpPublic(request: Request, env: Env): Promise<Response> {
  if (request.method === 'GET') {
    return jsonResponse({
      ok: true,
      protocolVersion: PROTOCOL_VERSION,
      serverInfo: SERVER_INFO,
      transport: 'streamable-http',
      auth: 'none',
      preview: true,
      tools: TOOLS.map((t) => ({ name: t.name, description: t.description })),
      hint: 'POST JSON-RPC 2.0 here. Public-safe preview — sanitized overviews only.',
      privateAlternative: {
        url: '/mcp',
        auth: 'x-athlete-memory-token header or Authorization: Bearer <token>',
        note: 'Full-fidelity tools (lane summaries, prompts, handoff, terminal_summary). NOT for public clients.',
      },
    });
  }

  if (request.method !== 'POST') {
    return jsonResponse(
      rpcError(null, -32600, 'POST or GET only.'),
      { status: 405, headers: { allow: 'GET, POST' } },
    );
  }

  // No auth check — this endpoint is intentionally public. The
  // strictly-sanitised tool surface above is what makes that safe.

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(rpcError(null, -32700, 'Parse error'), { status: 400 });
  }

  if (Array.isArray(body)) {
    const responses = await Promise.all(
      body.map((req) => handleRpcRequest(req as JsonRpcRequest, env)),
    );
    const filtered = responses.filter((r): r is JsonRpcResponse => r !== null);
    if (filtered.length === 0) return new Response(null, { status: 202 });
    return negotiated(request, filtered);
  }

  const response = await handleRpcRequest(body as JsonRpcRequest, env);
  if (response === null) return new Response(null, { status: 202 });
  return negotiated(request, response);
}
