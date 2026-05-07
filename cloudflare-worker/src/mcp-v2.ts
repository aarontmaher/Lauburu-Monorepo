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
import { buildOperatingRulesPayload } from './operating-rules';

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
const NATIVE_IPHONE_AUTOMATION_PRIORITY = {
  id: 'P0',
  title: 'Native iPhone automation controls from TestFlight app, not Expo-only',
  detail:
    'Add a mobile control-centre/automation path that works from the installed iPhone/TestFlight app, not just local Expo Go. Aaron can view live MCP project state and trigger only safe approved automation/control-centre actions from the native iPhone app with admin gating, no exposed secrets, and clear live/stale/fallback labels.',
  source: 'Aaron iPhone app request',
  safety: 'admin-gated',
  effort: 'medium',
  status: 'approved_active — top mobile priority above P1/P2',
  category: 'Product Direction — Active Mobile Priority',
  area: 'mobile-native-automation',
  raw: {
    id: 'P0',
    title: 'Native iPhone automation controls from TestFlight app, not Expo-only',
    detail:
      'Add a mobile control-centre/automation path that works from the installed iPhone/TestFlight app, not just local Expo Go. Aaron can view live MCP project state and trigger only safe approved automation/control-centre actions from the native iPhone app with admin gating, no exposed secrets, and clear live/stale/fallback labels.',
    source: 'Aaron iPhone app request',
    safety: 'admin-gated',
    effort: 'medium',
    status: 'approved_active — top mobile priority above P1/P2',
  },
} as const;

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
function corsHeaders(): Record<string, string> {
  return {
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'GET, POST, OPTIONS',
    'access-control-allow-headers': 'authorization, content-type, mcp-session-id, x-athlete-memory-token',
    'access-control-expose-headers': 'content-type, mcp-session-id',
  };
}
function optionsResponse(): Response {
  return new Response(null, { status: 204, headers: corsHeaders() });
}
function acceptedResponse(): Response {
  return new Response(null, { status: 202, headers: corsHeaders() });
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

async function buildProjectWorkStatus(env: Env): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      currentPriority: null,
      currentBlocker: null,
      nextAction: null,
      blocked: false,
      publicSafe: true,
    };
  }
  const work = await adapter.fetchSingleRowPayload('connector_work_status') as {
    currentPriority?: string | null;
    currentBlocker?: string | null;
    nextAction?: string | null;
  } | null;
  const currentPriority = typeof work?.currentPriority === 'string' ? work.currentPriority.slice(0, 280) : null;
  const currentBlocker = typeof work?.currentBlocker === 'string' && work.currentBlocker.length > 0
    ? work.currentBlocker.slice(0, 280) : null;
  const nextAction = typeof work?.nextAction === 'string' ? work.nextAction.slice(0, 280) : null;
  return {
    schemaVersion: 1,
    generatedAt,
    currentPriority,
    currentBlocker,
    nextAction,
    blocked: !!currentBlocker,
    publicSafe: true,
  };
}

/**
 * Canonical public-safe "what's happening right now" snapshot.
 *
 * Designed to be the single tool ChatGPT calls to disambiguate the
 * "MCP says all idle but Claude is working" confusion. Composes
 * priority + blocker + next action + per-lane sanitised
 * summaries + freshness + safety flags. No raw text > 140 chars
 * per field. No file paths. No prompt IDs.
 */
const FRESHNESS_WINDOW_MS_V2 = 10 * 60 * 1000;

/**
 * Canonical freshness signal used by every v2 tool that surfaces a
 * timestamped row. Keeping the shape identical across
 * project.get_current_state, mobile.get_*, and handoff.get_latest is
 * what makes "MCP fresh vs stale" a checkable invariant for rule 11.
 */
export interface FreshnessSignalV2 {
  updatedAt: string | null;
  ageMs: number | null;
  isStale: boolean;
  staleReason: 'fresh' | 'no_writeback' | 'env_missing';
  windowMs: number;
}

function computeFreshness(updatedAt: string | null, configured: boolean): FreshnessSignalV2 {
  if (!configured) {
    return { updatedAt: null, ageMs: null, isStale: true, staleReason: 'env_missing', windowMs: FRESHNESS_WINDOW_MS_V2 };
  }
  const ageMs = updatedAt ? Date.now() - new Date(updatedAt).getTime() : null;
  const isStale = ageMs === null ? true : ageMs > FRESHNESS_WINDOW_MS_V2;
  const staleReason: FreshnessSignalV2['staleReason'] = updatedAt === null
    ? 'no_writeback'
    : isStale ? 'no_writeback' : 'fresh';
  return { updatedAt, ageMs, isStale, staleReason, windowMs: FRESHNESS_WINDOW_MS_V2 };
}

async function buildProjectCurrentState(env: Env): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);

  const safetyBaseline = {
    publicSafe: true,
    privateFieldsWithheld: true,
    note: 'Public-safe surface. Per-lane lastSummary truncated to ≤140 char; prompt IDs / file paths / tokens dropped. Detail behind admin-token at /api/control_centre or mobile.get_control_centre.',
  } as const;

  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      source: 'placeholder' as const,
      freshness: {
        updatedAt: null,
        ageMs: null,
        isStale: true,
        staleReason: 'env_missing',
      },
      agents: [],
      currentPriority: null,
      currentBlocker: null,
      nextAction: null,
      liveStatus: { android: null, ios: null, repo: null },
      safety: safetyBaseline,
    };
  }

  const [work, lanes, build, handoff] = await Promise.all([
    adapter.fetchSingleRowPayload('connector_work_status') as Promise<{
      currentPriority?: string | null;
      currentBlocker?: string | null;
      nextAction?: string | null;
      generatedAt?: string;
      liveStatus?: { androidVersionCode?: number | null; iosBuildNumber?: string | null; androidPlayTrack?: string | null };
      repoStatus?: { branch?: string; head?: string };
    } | null>,
    adapter.fetchCoderLaneRows(),
    adapter.fetchSingleRowPayload('connector_build_status') as Promise<{
      generatedAt?: string;
      android?: { versionCode?: number | null; githubStatus?: string | null; playStatus?: string | null; playTrack?: string | null };
      ios?: { buildNumber?: string | null; githubStatus?: string | null; testflightStatus?: string | null };
    } | null>,
    adapter.fetchSingleRowPayload('connector_handoff') as Promise<{
      generatedAt?: string;
      agentQaResult?: unknown;
    } | null>,
  ]);

  const ALLOWED_LANE_STATUSES = ['idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done'] as const;
  const ALLOWED_LANE_IDS = ['claude', 'codex', 'claude_chat', 'chatgpt', 'cowork'] as const;

  function pickEnum<T extends string>(value: unknown, allowed: readonly T[]): T | 'unknown' {
    return typeof value === 'string' && (allowed as readonly string[]).includes(value)
      ? (value as T) : 'unknown';
  }

  function compressSummary(s: unknown): string {
    if (typeof s !== 'string' || s.length === 0) return '';
    return s.replace(/\s+/g, ' ').trim().slice(0, 140);
  }

  function safeShortCommit(s: unknown): string | null {
    if (typeof s !== 'string') return null;
    return /^[0-9a-f]{7,12}$/.test(s) ? s : null;
  }

  const agents = (lanes ?? []).map((row) => {
    const p = (row.payload ?? {}) as {
      laneId?: string;
      status?: string;
      lastSummary?: string;
      lastCommit?: string;
      lastSeenAt?: string;
    };
    return {
      id: pickEnum(row.lane_id, ALLOWED_LANE_IDS),
      status: pickEnum(p.status, ALLOWED_LANE_STATUSES),
      taskSummary: compressSummary(p.lastSummary),
      lastCommit: safeShortCommit(p.lastCommit),
      updatedAt: typeof p.lastSeenAt === 'string' ? p.lastSeenAt : null,
    };
  });

  const truncate = (s: string | null | undefined, cap: number) => {
    if (typeof s !== 'string' || !s) return null;
    return s.length > cap ? `${s.slice(0, cap - 1)}…` : s;
  };
  const currentPriority = truncate(work?.currentPriority ?? null, 280);
  const currentBlocker = truncate(work?.currentBlocker ?? null, 280);
  const nextAction = truncate(work?.nextAction ?? null, 280);

  const ANDROID_PRIO: Array<{ match: (s: { gh?: string; play?: string }) => boolean; label: 'live' | 'repo-only' | 'tester-build' | 'blocked' }> = [
    { match: (s) => s.gh === 'failure' || s.play === 'failed', label: 'blocked' },
    { match: (s) => s.play === 'rolled_out' || s.play === 'submitted_completed', label: 'live' },
    { match: (s) => s.play === 'submitted_draft' || s.gh === 'success' || s.gh === 'in_progress', label: 'tester-build' },
  ];
  const IOS_PRIO: Array<{ match: (s: { gh?: string; tf?: string }) => boolean; label: 'live' | 'repo-only' | 'tester-build' | 'blocked' }> = [
    { match: (s) => s.gh === 'failure' || s.tf === 'failed' || s.tf === 'invalid_binary', label: 'blocked' },
    { match: (s) => s.tf === 'available', label: 'live' },
    { match: (s) => s.tf === 'uploaded_processing' || s.gh === 'success', label: 'tester-build' },
  ];
  const a = build?.android ?? {};
  const i = build?.ios ?? {};
  let androidStatus: 'live' | 'repo-only' | 'tester-build' | 'blocked' = 'repo-only';
  for (const r of ANDROID_PRIO) {
    if (r.match({ gh: typeof a.githubStatus === 'string' ? a.githubStatus : undefined, play: typeof a.playStatus === 'string' ? a.playStatus : undefined })) { androidStatus = r.label; break; }
  }
  let iosStatus: 'live' | 'repo-only' | 'tester-build' | 'blocked' = 'repo-only';
  for (const r of IOS_PRIO) {
    if (r.match({ gh: typeof i.githubStatus === 'string' ? i.githubStatus : undefined, tf: typeof i.testflightStatus === 'string' ? i.testflightStatus : undefined })) { iosStatus = r.label; break; }
  }

  // Source row updatedAt → freshness signal.
  const isoCandidates = [
    typeof work?.generatedAt === 'string' ? work.generatedAt : null,
    typeof build?.generatedAt === 'string' ? build.generatedAt : null,
    ...agents.map((g) => g.updatedAt),
  ].filter((s): s is string => typeof s === 'string');
  const updatedAt = isoCandidates.length > 0 ? isoCandidates.sort().slice(-1)[0] : null;
  const ageMs = updatedAt ? Date.now() - new Date(updatedAt).getTime() : null;
  const isStale = ageMs === null ? true : ageMs > FRESHNESS_WINDOW_MS_V2;
  const staleReason: 'fresh' | 'no_writeback' | 'env_missing' = updatedAt === null
    ? 'no_writeback' : isStale ? 'no_writeback' : 'fresh';

  const branchRe = /^[A-Za-z0-9._\-/]{1,80}$/;
  const branch = work?.repoStatus?.branch && branchRe.test(work.repoStatus.branch) ? work.repoStatus.branch : null;
  const head = safeShortCommit(work?.repoStatus?.head);
  const latestQaGate = buildPublicQaGate(handoff?.agentQaResult ?? null);

  const haveAnyRow = work !== null || (lanes !== null && lanes.length > 0) || build !== null || handoff !== null;

  return {
    schemaVersion: 1,
    generatedAt,
    source: haveAnyRow ? 'supabase' as const : 'placeholder' as const,
    freshness: {
      updatedAt,
      ageMs,
      isStale,
      staleReason,
      windowMs: FRESHNESS_WINDOW_MS_V2,
    },
    agents,
    currentPriority,
    currentBlocker,
    nextAction,
    liveStatus: {
      android: {
        versionCode: typeof a.versionCode === 'number' ? a.versionCode : null,
        status: androidStatus,
        playTrack: typeof a.playTrack === 'string' ? a.playTrack : null,
      },
      ios: {
        buildNumber: typeof i.buildNumber === 'string' ? i.buildNumber : null,
        status: iosStatus,
      },
      repo: { branch, shortHead: head },
    },
    latestQaGate,
    safety: safetyBaseline,
  };
}

function buildPublicQaGate(qa: unknown): unknown | null {
  if (!qa || typeof qa !== 'object') return null;
  const value = qa as Record<string, unknown>;
  const releaseGate = value.releaseGate && typeof value.releaseGate === 'object'
    ? value.releaseGate as Record<string, unknown>
    : {};
  const installedBuild = value.installedBuild && typeof value.installedBuild === 'object'
    ? value.installedBuild as Record<string, unknown>
    : {};
  const repo = value.repo && typeof value.repo === 'object'
    ? value.repo as Record<string, unknown>
    : {};
  const updatedAt = typeof value.updatedAt === 'string' ? value.updatedAt : null;
  const freshness = computeFreshness(updatedAt, true);
  const status = typeof value.status === 'string' ? value.status : 'unknown';
  const gateBlockedReason = freshness.isStale
    ? 'QA result is stale; installed-device build gates remain blocked.'
    : status !== 'pass'
      ? `${status} QA does not clear installed-device build gates.`
      : null;
  const rawReason = typeof releaseGate.reason === 'string' ? releaseGate.reason.slice(0, 280) : 'No release gate reason recorded.';
  return {
    status,
    gate: typeof value.gate === 'string' ? value.gate : 'general',
    platform: typeof value.platform === 'string' ? value.platform : 'repo',
    updatedAt,
    freshness,
    installedBuild: {
      iosBuildNumber: typeof installedBuild.iosBuildNumber === 'string' ? installedBuild.iosBuildNumber : null,
      androidVersionCode: typeof installedBuild.androidVersionCode === 'number' ? installedBuild.androidVersionCode : null,
      appVersion: typeof installedBuild.appVersion === 'string' ? installedBuild.appVersion : null,
      channel: typeof installedBuild.channel === 'string' ? installedBuild.channel : null,
      track: typeof installedBuild.track === 'string' ? installedBuild.track : null,
    },
    repo: {
      branch: typeof repo.branch === 'string' ? repo.branch.slice(0, 80) : null,
      shortHead: typeof repo.shortHead === 'string' && /^[0-9a-f]{7,12}$/.test(repo.shortHead) ? repo.shortHead : null,
    },
    releaseGate: {
      newTestFlightAllowed: gateBlockedReason ? false : releaseGate.newTestFlightAllowed === true,
      newAndroidBuildAllowed: gateBlockedReason ? false : releaseGate.newAndroidBuildAllowed === true,
      reason: gateBlockedReason ? `${gateBlockedReason} ${rawReason}`.slice(0, 280) : rawReason,
    },
    publicSummary: typeof value.publicSummary === 'string' ? value.publicSummary.slice(0, 280) : null,
    publicSafe: true,
  };
}

async function buildProjectListPriorities(env: Env): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  const items: Array<{ source: 'mobile'; rank: number; title: string; status: string }> = [];
  items.push({
    source: 'mobile',
    rank: 0,
    title: NATIVE_IPHONE_AUTOMATION_PRIORITY.title,
    status: NATIVE_IPHONE_AUTOMATION_PRIORITY.status,
  });
  if (adapter.configured) {
    const top = await adapter.fetchTopBacklogItem();
    if (top && top.title !== NATIVE_IPHONE_AUTOMATION_PRIORITY.title) {
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

function withNativeIphoneAutomationPriority(payload: unknown): unknown {
  const priority = NATIVE_IPHONE_AUTOMATION_PRIORITY;
  if (Array.isArray(payload)) {
    const exists = payload.some((item) => (
      item && typeof item === 'object' && (item as { title?: unknown }).title === priority.title
    ));
    return exists ? payload : [priority, ...payload];
  }
  if (payload && typeof payload === 'object') {
    const obj = payload as { items?: unknown; count?: unknown };
    if (Array.isArray(obj.items)) {
      const exists = obj.items.some((item) => (
        item && typeof item === 'object' && (item as { title?: unknown }).title === priority.title
      ));
      if (exists) return payload;
      return {
        ...payload,
        count: typeof obj.count === 'number' ? obj.count + 1 : obj.items.length + 1,
        items: [priority, ...obj.items],
      };
    }
  }
  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    items: [priority],
    count: 1,
    source: 'repo_overlay',
    note: 'Website MCP suggestion list was unavailable or returned an unsupported shape; top priority is repo-backed by unified MCP v2.',
  };
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
      apple_health: {
        exposure: 'ios-only',
        userVisible: true,
        readinessRole: 'primary_ios',
      },
      health_connect: {
        exposure: 'android-only',
        userVisible: true,
        readinessRole: 'primary_android',
      },
      manual_journal: {
        exposure: 'all-platforms',
        userVisible: true,
        readinessRole: 'context',
      },
      whoop_oauth: {
        exposure: 'optional-backfill',
        userVisible: false,
        readinessRole: 'not_core_readiness',
        note: 'WHOOP Direct is not a core readiness source. Historical CSV/export data may be used only as optional labelled backfill/provisional evidence.',
      },
      polar_oauth: {
        exposure: 'optional-backfill',
        userVisible: false,
        readinessRole: 'not_core_readiness',
        note: 'Polar Direct is not a core readiness source. Hub-fed Polar provenance stays labelled via Apple Health / Health Connect; direct Polar remains optional/backfill only.',
      },
    },
    note: 'Core readiness sources are Apple Health on iOS, Health Connect on Android, and manual/journal context. WHOOP Direct and Polar Direct are not core readiness providers; public output exposes no personal metrics.',
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
  // Freshness anchor = newest mobile-source entry (mirror of
  // connector_handoff). Website entries stay informational; their
  // generatedAt does not gate freshness because the website MCP write
  // path is currently unauthorised from this worker (see
  // docs/MCP_CANONICAL_STATE.md).
  const mobileEntry = entries.find((e) => e.source === 'mobile') ?? null;
  return {
    schemaVersion: 1,
    generatedAt,
    source: adapter.configured && mobileEntry ? ('supabase' as const) : ('placeholder' as const),
    freshness: computeFreshness(mobileEntry?.generatedAt ?? null, adapter.configured),
    entries,
    publicPreview: true,
  };
}

async function buildQaLatestResult(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const generatedAt = new Date().toISOString();
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      source: 'placeholder' as const,
      freshness: computeFreshness(null, false),
      latestQaGate: null,
      publicPreview: true,
    };
  }
  const payload = await adapter.fetchSingleRowPayload('connector_handoff') as {
    agentQaResult?: unknown;
  } | null;
  const latestQaGate = buildPublicQaGate(payload?.agentQaResult ?? null);
  const updatedAt = latestQaGate && typeof latestQaGate === 'object'
    ? (latestQaGate as { updatedAt?: unknown }).updatedAt
    : null;
  return {
    schemaVersion: 1,
    generatedAt,
    source: latestQaGate ? ('supabase' as const) : ('placeholder' as const),
    freshness: computeFreshness(typeof updatedAt === 'string' ? updatedAt : null, true),
    latestQaGate,
    publicPreview: true,
  };
}

async function buildMobileAgentQaResult(env: Env): Promise<unknown> {
  const full = await buildMobileFullSingle(env, 'connector_handoff') as {
    payload?: { agentQaResult?: unknown } | null;
    freshness?: unknown;
    source?: unknown;
  };
  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    source: full.source ?? 'placeholder',
    freshness: full.freshness,
    payload: full.payload?.agentQaResult ?? null,
  };
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
  const generatedAt = new Date().toISOString();
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      source: 'placeholder' as const,
      freshness: computeFreshness(null, false),
      payload: null,
      error: 'supabase not configured',
    };
  }
  const payload = (await adapter.fetchSingleRowPayload(table)) ?? null;
  // Row-level updatedAt comes from payload.generatedAt (the row's
  // canonical timestamp written by the bridge). The Postgres
  // generated_at column is what the bridge mirrors into payload.
  const updatedAt = (payload && typeof (payload as { generatedAt?: unknown }).generatedAt === 'string')
    ? (payload as { generatedAt: string }).generatedAt
    : null;
  return {
    schemaVersion: 1,
    generatedAt,
    source: payload ? ('supabase' as const) : ('placeholder' as const),
    freshness: computeFreshness(updatedAt, true),
    payload,
  };
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
  inputSchema: unknown;
  auth: 'public' | 'admin';
  build: (env: Env, args?: unknown) => Promise<unknown>;
}

const SECRET_PATTERNS = [
  /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g,
  /\bsk-[A-Za-z0-9_-]{16,}\b/g,
  /\bghp_[A-Za-z0-9]{20,}\b/g,
  /\bgho_[A-Za-z0-9]{20,}\b/g,
  /\bghs_[A-Za-z0-9]{20,}\b/g,
  /\bwhsec_[A-Za-z0-9]{20,}\b/g,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /\bxox[abprs]-[A-Za-z0-9-]{20,}/g,
] as const;

function sanitizeStatusText(value: unknown, cap: number): string | null {
  if (typeof value !== 'string') return null;
  let out = value.replace(/\s+/g, ' ').trim();
  if (!out) return null;
  for (const pattern of SECRET_PATTERNS) out = out.replace(pattern, '<redacted>');
  return out.length > cap ? `${out.slice(0, cap - 1)}…` : out;
}

function parseWorkStatusArgs(args: unknown): {
  agent: 'claude' | 'codex' | 'claude_chat' | 'chatgpt' | 'cowork';
  laneStatus: 'idle' | 'working' | 'blocked' | 'needs_user' | 'needs_review' | 'done';
  requestedStatus: string;
  task: string;
  summary: string | null;
  branch: string | null;
  commit: string | null;
} | { error: string } {
  const input = (args && typeof args === 'object') ? args as Record<string, unknown> : {};
  const agentRaw = sanitizeStatusText(input.agent, 40);
  const AGENTS = ['claude', 'codex', 'claude_chat', 'chatgpt', 'cowork'] as const;
  const agentAlias: Record<string, typeof AGENTS[number]> = {
    claude: 'claude',
    codex: 'codex',
    claude_chat: 'claude_chat',
    'claude-code-guide': 'claude_chat',
    chatgpt: 'chatgpt',
    cowork: 'cowork',
  };
  const agent = agentRaw ? agentAlias[agentRaw] : undefined;
  if (!agent || !(AGENTS as readonly string[]).includes(agent)) return { error: 'agent must be one of claude, codex, claude_chat, chatgpt, cowork' };

  const task = sanitizeStatusText(input.task, 140);
  if (!task) return { error: 'task is required' };
  const requestedStatus = sanitizeStatusText(input.status, 80) ?? 'working';
  const statusMap: Record<string, typeof LANE_STATUSES[number]> = {
    idle: 'idle',
    working: 'working',
    in_progress: 'working',
    blocked: 'blocked',
    needs_user: 'needs_user',
    needs_review: 'needs_review',
    'implementation-complete-awaiting-agent-confirmation': 'needs_review',
    done: 'done',
  };
  const laneStatus = statusMap[requestedStatus] ?? 'needs_review';
  const summary = sanitizeStatusText(input.summary, 240);
  const branchCandidate = sanitizeStatusText(input.branch, 80);
  const branch = branchCandidate && /^[A-Za-z0-9._\-/]{1,80}$/.test(branchCandidate) ? branchCandidate : null;
  const commitCandidate = sanitizeStatusText(input.commit, 12);
  const commit = commitCandidate && /^[0-9a-f]{7,12}$/.test(commitCandidate) ? commitCandidate : null;
  return { agent, laneStatus, requestedStatus, task, summary, branch, commit };
}

const LANE_STATUSES = ['idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done'] as const;

async function updateProjectWorkStatus(env: Env, args?: unknown): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const generatedAt = new Date().toISOString();
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      ok: false,
      error: adapter.reason,
      message: 'Supabase writer env is not configured on this Worker.',
    };
  }
  const parsed = parseWorkStatusArgs(args);
  if ('error' in parsed) {
    return { schemaVersion: 1, generatedAt, ok: false, error: parsed.error };
  }

  const lanePayload = {
    laneId: parsed.agent,
    status: parsed.laneStatus,
    statusDetail: parsed.requestedStatus,
    lastSeenAt: generatedAt,
    currentPromptId: null,
    lastPromptId: null,
    lastSummary: parsed.summary ? `${parsed.task}. ${parsed.summary}` : parsed.task,
    lastCommit: parsed.commit,
    lastTypecheckResult: null,
    dirtyFiles: [],
    nextPrompt: null,
  };
  const workPayload = {
    schemaVersion: 1,
    generatedAt,
    currentPriority: parsed.task,
    currentBlocker: parsed.laneStatus === 'blocked' ? parsed.summary : null,
    liveStatus: {
      androidVersionCode: null,
      iosBuildNumber: null,
      androidPlayTrack: null,
      iosTestflightGroup: null,
      lastRailwayDeployAt: null,
      cloudflareWorkerDeployed: true,
    },
    repoStatus: {
      head: parsed.commit,
      branch: parsed.branch ?? 'main',
      dirtyFileCount: 0,
      untrackedFileCount: 0,
      lastCommitAt: generatedAt,
      lastCommitMessage: parsed.summary ?? parsed.task,
    },
    nextAction: parsed.laneStatus === 'needs_review'
      ? 'Agent functional re-audit next; no EAS build until Agent confirms and Aaron approves.'
      : (parsed.summary ?? parsed.task),
  };

  const [workResult, laneResult] = await Promise.all([
    adapter.upsertWorkStatus(workPayload, generatedAt),
    adapter.upsertCoderLane(parsed.agent, lanePayload, generatedAt),
  ]);
  if (!workResult.ok || !laneResult.ok) {
    return {
      schemaVersion: 1,
      generatedAt,
      ok: false,
      workStatus: workResult.ok ? 'ok' : `HTTP ${workResult.status}`,
      coderLane: laneResult.ok ? 'ok' : `HTTP ${laneResult.status}`,
    };
  }
  return {
    schemaVersion: 1,
    generatedAt,
    ok: true,
    agent: parsed.agent,
    status: parsed.laneStatus,
    statusDetail: parsed.requestedStatus,
    task: parsed.task,
    commit: parsed.commit,
  };
}

async function submitProjectPrioritySuggestion(_env: Env, args?: unknown): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  const input = (args && typeof args === 'object') ? args as Record<string, unknown> : {};
  const title = sanitizeStatusText(input.title, 160);
  if (!title) {
    return { schemaVersion: 1, generatedAt, ok: false, error: 'title is required' };
  }
  const detail = sanitizeStatusText(input.detail, 700);
  const source = sanitizeStatusText(input.source, 120) ?? 'admin MCP';
  const area = sanitizeStatusText(input.area, 80) ?? 'mobile-native-automation';
  const isNativeIphonePriority = title === NATIVE_IPHONE_AUTOMATION_PRIORITY.title;

  return {
    schemaVersion: 1,
    generatedAt,
    ok: true,
    accepted: true,
    id: isNativeIphonePriority ? NATIVE_IPHONE_AUTOMATION_PRIORITY.id : 'admin-suggestion',
    rank: isNativeIphonePriority ? 0 : null,
    title,
    detail,
    source,
    area,
    auth: 'admin-token',
    durability: isNativeIphonePriority ? 'repo-backed priority overlay' : 'admin-gated intake only',
    note: isNativeIphonePriority
      ? 'This priority is already surfaced at rank 0 by unified MCP v2.'
      : 'Generic durable suggestion storage is not enabled yet; add approved priorities to the repo/backlog source after Aaron approval.',
    publicWriteAllowed: false,
  };
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
    name: 'project.get_current_state',
    description: 'Canonical "what is the team working on right now" snapshot. Composes priority / blocker / next action + per-lane (claude / codex) status + sanitised task summaries (≤140 char) + Android v + iOS Build state + freshness flag. Public-safe; the source enum + staleReason fields make it explicit when data is older than the 10-min freshness window. Use this from ChatGPT instead of the website MCP when you want current dev state.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildProjectCurrentState,
  },
  {
    name: 'project.get_work_status',
    description: 'Sanitised work status — currentPriority, currentBlocker, nextAction (each ≤280 char) plus a blocked boolean. No raw text fields beyond those three. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildProjectWorkStatus,
  },
  {
    name: 'project.update_work_status',
    description: 'Admin-token-gated writeback for the mobile project work-status and coder-lane Supabase rows. Sanitizes text, maps implementation-complete-awaiting-agent-confirmation to needs_review, and never stores secrets.',
    inputSchema: {
      type: 'object',
      properties: {
        agent: { type: 'string', enum: ['claude', 'codex', 'claude_chat', 'chatgpt', 'cowork'] },
        status: { type: 'string' },
        task: { type: 'string' },
        summary: { type: 'string' },
        branch: { type: 'string' },
        commit: { type: 'string' },
      },
      required: ['agent', 'status', 'task'],
    },
    auth: 'admin',
    build: updateProjectWorkStatus,
  },
  {
    name: 'update_work_status',
    description: 'Compatibility alias for project.update_work_status. Admin token required.',
    inputSchema: {
      type: 'object',
      properties: {
        agent: { type: 'string' },
        status: { type: 'string' },
        task: { type: 'string' },
        summary: { type: 'string' },
        branch: { type: 'string' },
        commit: { type: 'string' },
      },
      required: ['agent', 'status', 'task'],
    },
    auth: 'admin',
    build: updateProjectWorkStatus,
  },
  {
    name: 'project.submit_priority_suggestion',
    description: 'Admin-token-gated priority suggestion intake for unified MCP v2. Public No Auth clients are rejected; no secrets are returned. Current native iPhone automation item is repo-backed at rank 0.',
    inputSchema: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        detail: { type: 'string' },
        source: { type: 'string' },
        area: { type: 'string' },
      },
      required: ['title'],
    },
    auth: 'admin',
    build: submitProjectPrioritySuggestion,
  },
  {
    name: 'submit_priority_suggestion',
    description: 'Compatibility alias for project.submit_priority_suggestion. Admin token required.',
    inputSchema: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        detail: { type: 'string' },
        source: { type: 'string' },
        area: { type: 'string' },
      },
      required: ['title'],
    },
    auth: 'admin',
    build: submitProjectPrioritySuggestion,
  },
  {
    name: 'project.get_operating_rules',
    description: 'Returns the canonical 14 operating rules every coder / agent / consumer must follow (audit→bundles, parallel lanes, no stopping at one patch, re-audit on implementation-complete, Agent-confirmed gate, EAS build cost control, no "fully done" without Aaron, provisional health claims, repo docs as source of truth, MCP-first start, coders run all laptop commands, clear-steps automate-first, parallel priorities stay active). Stable rule IDs 1..14 + titles + bodies. Mirror of docs/OPERATING_RULES.md. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: async () => buildOperatingRulesPayload(),
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
  {
    name: 'qa.get_latest_result',
    description: 'Latest public-safe Agent QA gate summary. Shows repo-only vs installed-device QA status, tested platform/build, and whether TestFlight/Internal QA build is allowed. No screenshots, private details, or raw logs.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    build: buildQaLatestResult,
  },
  {
    name: 'mobile.get_agent_qa_result',
    description: 'Full latest Agent QA result carried by connector_handoff.agentQaResult. Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    build: buildMobileAgentQaResult,
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
      const rawPayload = await proxyWebsiteCall(upstream, args ?? {});
      const payload = upstream === 'list_pending_suggestions'
        ? withNativeIphoneAutomationPriority(rawPayload)
        : rawPayload;
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
  const payload = await tool.build(env, args);
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
  if (request.method === 'OPTIONS') {
    return optionsResponse();
  }

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
    if (filtered.length === 0) return acceptedResponse();
    return negotiated(request, filtered);
  }
  const response = await handleRpcRequest(body as JsonRpcRequest, env, request);
  if (response === null) return acceptedResponse();
  return negotiated(request, response);
}

export async function handleMcpV2Health(request: Request, env: Env): Promise<Response> {
  if (request.method === 'OPTIONS') {
    return optionsResponse();
  }
  if (request.method !== 'GET') {
    return jsonResponse(rpcError(null, -32600, 'GET only.'), { status: 405, headers: { allow: 'GET, OPTIONS' } });
  }
  const adapter = getSupabaseAdapter(env);
  let source: 'supabase' | 'repo-only' = 'repo-only';
  if (adapter.configured) {
    const ping = await adapter.ping();
    if (ping.ok) source = 'supabase';
  }
  return jsonResponse({
    ok: true,
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    protocolVersion: PROTOCOL_VERSION,
    serverInfo: SERVER_INFO,
    transport: 'streamable-http',
    supportedTransports: ['streamable-http', 'sse-framed-json-rpc'],
    source,
    requiredTools: [
      'project.get_current_state',
      'project.get_operating_rules',
      'integrations.get_overview',
      'handoff.get_latest',
      'qa.get_latest_result',
    ],
  });
}
