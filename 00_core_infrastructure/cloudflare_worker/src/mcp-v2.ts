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

const TEXT_SECRET_PATTERNS: ReadonlyArray<RegExp> = [
  /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g,
  /\bsk-[A-Za-z0-9_-]{16,}\b/g,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/g,
  /\bwhsec_[A-Za-z0-9]{20,}\b/g,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /\bsb_secret_[A-Za-z0-9_-]{20,}\b/g,
];

function redactText(value: unknown, cap = 1000): string | null {
  if (typeof value !== 'string' || value.length === 0) return null;
  let text = value.replace(/\s+/g, ' ').trim();
  for (const pattern of TEXT_SECRET_PATTERNS) text = text.replace(pattern, '<redacted>');
  return text.length > cap ? `${text.slice(0, Math.max(0, cap - 1)).trim()}…` : text;
}

function safeShortCommit(value: unknown): string | null {
  return typeof value === 'string' && /^[0-9a-f]{7,12}$/.test(value) ? value : null;
}

function safeIso(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function currentQaBuildTargets(qa: unknown): { iosBuildNumber: string | null; androidVersionCode: number | null; appVersion: string | null } {
  if (!qa || typeof qa !== 'object') return { iosBuildNumber: '19', androidVersionCode: 18, appVersion: '0.1.0' };
  const installed = (qa as { installedBuild?: unknown }).installedBuild;
  if (!installed || typeof installed !== 'object') return { iosBuildNumber: '19', androidVersionCode: 18, appVersion: '0.1.0' };
  const row = installed as { iosBuildNumber?: unknown; androidVersionCode?: unknown; appVersion?: unknown };
  return {
    iosBuildNumber: typeof row.iosBuildNumber === 'string' ? row.iosBuildNumber : '19',
    androidVersionCode: typeof row.androidVersionCode === 'number' ? row.androidVersionCode : 18,
    appVersion: typeof row.appVersion === 'string' ? row.appVersion : '0.1.0',
  };
}

function sanitizeQaResult(qa: unknown, detail: 'public' | 'admin'): unknown | null {
  if (!qa || typeof qa !== 'object') return null;
  const row = qa as Record<string, unknown>;
  const releaseGate = row.releaseGate && typeof row.releaseGate === 'object'
    ? row.releaseGate as Record<string, unknown>
    : {};
  const installed = row.installedBuild && typeof row.installedBuild === 'object'
    ? row.installedBuild as Record<string, unknown>
    : {};
  const repo = row.repo && typeof row.repo === 'object'
    ? row.repo as Record<string, unknown>
    : {};
  const results = row.results && typeof row.results === 'object'
    ? row.results as Record<string, unknown>
    : {};
  const evidence = row.evidence && typeof row.evidence === 'object'
    ? row.evidence as Record<string, unknown>
    : {};
  const requiredFixes = Array.isArray(row.requiredFixes)
    ? row.requiredFixes.map((item) => redactText(item, 180)).filter((item): item is string => !!item).slice(0, detail === 'admin' ? 20 : 5)
    : [];
  const base = {
    schemaVersion: 1,
    qaRunId: detail === 'admin' ? redactText(row.qaRunId, 80) : null,
    sourceAgent: redactText(row.sourceAgent, 80),
    createdAt: safeIso(row.createdAt),
    updatedAt: safeIso(row.updatedAt),
    status: typeof row.status === 'string' ? row.status : 'unknown',
    gate: typeof row.gate === 'string' ? row.gate : 'general',
    platform: typeof row.platform === 'string' ? row.platform : 'repo',
    deviceName: detail === 'admin' ? redactText(row.deviceName, 120) : null,
    installedBuild: {
      iosBuildNumber: typeof installed.iosBuildNumber === 'string' ? installed.iosBuildNumber : null,
      androidVersionCode: typeof installed.androidVersionCode === 'number' ? installed.androidVersionCode : null,
      appVersion: typeof installed.appVersion === 'string' ? installed.appVersion : null,
      channel: typeof installed.channel === 'string' ? installed.channel : null,
      track: typeof installed.track === 'string' ? installed.track : null,
    },
    repo: {
      branch: typeof repo.branch === 'string' ? repo.branch.slice(0, 80) : null,
      shortHead: safeShortCommit(repo.shortHead),
    },
    results: {
      healthManageSources: typeof results.healthManageSources === 'string' ? results.healthManageSources : 'not_tested',
      androidHealthConnect: typeof results.androidHealthConnect === 'string' ? results.androidHealthConnect : 'not_tested',
      iosAppleHealth: typeof results.iosAppleHealth === 'string' ? results.iosAppleHealth : 'not_tested',
      grapplingReadiness: typeof results.grapplingReadiness === 'string' ? results.grapplingReadiness : 'not_tested',
      adminControlCentre: typeof results.adminControlCentre === 'string' ? results.adminControlCentre : 'not_tested',
      copyTruthfulness: typeof results.copyTruthfulness === 'string' ? results.copyTruthfulness : 'not_tested',
      uiDensity: typeof results.uiDensity === 'string' ? results.uiDensity : 'not_tested',
    },
    releaseGate: {
      newTestFlightAllowed: releaseGate.newTestFlightAllowed === true,
      newAndroidBuildAllowed: releaseGate.newAndroidBuildAllowed === true,
      reason: redactText(releaseGate.reason, 280) ?? 'No release gate reason recorded.',
    },
    requiredFixes,
    publicSummary: redactText(row.publicSummary, 280),
  };
  if (detail === 'public') return { ...base, qaRunId: undefined, deviceName: undefined, publicSafe: true };
  return {
    ...base,
    evidence: {
      screenshotRefs: Array.isArray(evidence.screenshotRefs)
        ? evidence.screenshotRefs.map((item) => redactText(item, 120)).filter((item): item is string => !!item).slice(0, 20)
        : [],
      notes: redactText(evidence.notes, 1000),
    },
    privateDetails: redactText(row.privateDetails, 1000),
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
export const ACTIVE_LANE_STALE_MS_V2 = 60 * 1000;
export const IDLE_LANE_STALE_MS_V2 = 120 * 1000;
export const BUILD_AUDIT_STALE_MS_V2 = 180 * 1000;

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
  staleReason: 'fresh' | 'no_writeback' | 'stale_writeback' | 'env_missing';
  windowMs: number;
}

function computeFreshnessWithWindow(updatedAt: string | null, configured: boolean, windowMs: number, nowMs = Date.now()): FreshnessSignalV2 {
  if (!configured) {
    return { updatedAt: null, ageMs: null, isStale: true, staleReason: 'env_missing', windowMs };
  }
  const ageMs = updatedAt ? nowMs - new Date(updatedAt).getTime() : null;
  const isStale = ageMs === null ? true : ageMs > windowMs;
  // staleReason distinguishes:
  //   - no_writeback: row never written (updatedAt === null)
  //   - stale_writeback: row written but older than the freshness window
  //   - fresh: row within the window
  // Consumers (Admin/Dev pill, push gate trigger, audit playbook) MUST
  // treat both no_writeback and stale_writeback as unreliable per the
  // mcpLivenessP0 rule (connector_work_status.mcpLivenessP0).
  const staleReason: FreshnessSignalV2['staleReason'] = updatedAt === null
    ? 'no_writeback'
    : isStale ? 'stale_writeback' : 'fresh';
  return { updatedAt, ageMs, isStale, staleReason, windowMs };
}

export function computeFreshness(updatedAt: string | null, configured: boolean, nowMs = Date.now()): FreshnessSignalV2 {
  return computeFreshnessWithWindow(updatedAt, configured, FRESHNESS_WINDOW_MS_V2, nowMs);
}

export interface LaneHeartbeatSignalV2 {
  lastSeenAt: string | null;
  heartbeatAgeMs: number | null;
  isStale: boolean;
  staleReason: 'fresh' | 'no_heartbeat' | 'active_heartbeat_stale' | 'idle_heartbeat_stale';
  windowMs: number;
}

function laneHeartbeatWindowMs(status: string): number {
  return status === 'working' || status === 'in_progress'
    ? ACTIVE_LANE_STALE_MS_V2
    : IDLE_LANE_STALE_MS_V2;
}

export function computeLaneHeartbeat(
  status: string,
  lastSeenAt: string | null,
  nowMs = Date.now(),
): LaneHeartbeatSignalV2 {
  const windowMs = laneHeartbeatWindowMs(status);
  const heartbeatAgeMs = lastSeenAt ? nowMs - new Date(lastSeenAt).getTime() : null;
  const isStale = heartbeatAgeMs === null ? true : heartbeatAgeMs > windowMs;
  const staleReason: LaneHeartbeatSignalV2['staleReason'] = heartbeatAgeMs === null
    ? 'no_heartbeat'
    : isStale
      ? (windowMs === ACTIVE_LANE_STALE_MS_V2 ? 'active_heartbeat_stale' : 'idle_heartbeat_stale')
      : 'fresh';
  return { lastSeenAt, heartbeatAgeMs, isStale, staleReason, windowMs };
}

export function latestIsoTimestamp(candidates: Array<string | null | undefined>): string | null {
  const isoCandidates = candidates.filter((s): s is string => typeof s === 'string' && s.length > 0);
  return isoCandidates.length > 0 ? isoCandidates.sort().slice(-1)[0] : null;
}

export function effectiveAgentStatusForFreshness(
  status: string,
  freshness: Pick<FreshnessSignalV2, 'isStale'>,
  laneHeartbeat?: Pick<LaneHeartbeatSignalV2, 'isStale'>,
): string {
  if ((freshness.isStale || laneHeartbeat?.isStale) && (status === 'working' || status === 'in_progress')) {
    return 'idle';
  }
  return status;
}

export async function buildProjectCurrentState(env: Env): Promise<unknown> {
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
      updatedAt?: string;
      longRunning?: boolean;
      android?: { versionCode?: number | null; githubStatus?: string | null; playStatus?: string | null; playTrack?: string | null };
      ios?: { buildNumber?: string | null; githubStatus?: string | null; testflightStatus?: string | null };
    } | null>,
    adapter.fetchSingleRowPayload('connector_handoff') as Promise<{
      generatedAt?: string;
      updatedAt?: string;
      longRunning?: boolean;
      agentQaResult?: unknown;
      actionLedger?: unknown;
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

  const agentRows = (lanes ?? []).map((row) => {
    const p = (row.payload ?? {}) as {
      laneId?: string;
      status?: string;
      lastSummary?: string;
      lastCommit?: string;
      lastSeenAt?: string;
      lastStateChangeAt?: string;
      terminalStatus?: string;
      lastEventType?: string;
      lastEventAt?: string;
      source?: string;
      lastMarkers?: {
        MCP_RESULT?: string | null;
        MCP_BLOCKER?: string | null;
        MCP_COMMIT?: string | null;
        MCP_TESTS?: string | null;
        MCP_NEXT?: string | null;
        AGENT_QA_RESULT_JSON?: { status?: string | null; gate?: string | null; platform?: string | null } | null;
        markerCount?: number;
        markerHash?: string;
      };
    };
    const lastSeenAt = typeof p.lastSeenAt === 'string' ? p.lastSeenAt : null;
    const lastStateChangeAt = typeof p.lastStateChangeAt === 'string' ? p.lastStateChangeAt : null;
    const m = p.lastMarkers && typeof p.lastMarkers === 'object' ? p.lastMarkers : null;
    const cleanString = (v: unknown, cap: number): string | null => {
      if (typeof v !== 'string' || v.length === 0) return null;
      const t = redactText(v, cap);
      return t && t.length > 0 ? t : null;
    };
    const lastMarkers = m
      ? {
          MCP_RESULT: cleanString(m.MCP_RESULT, 280),
          MCP_BLOCKER: cleanString(m.MCP_BLOCKER, 280),
          MCP_COMMIT: cleanString(m.MCP_COMMIT, 80),
          MCP_TESTS: cleanString(m.MCP_TESTS, 280),
          MCP_NEXT: cleanString(m.MCP_NEXT, 280),
          AGENT_QA_RESULT_JSON: m.AGENT_QA_RESULT_JSON && typeof m.AGENT_QA_RESULT_JSON === 'object'
            ? {
                status: cleanString(m.AGENT_QA_RESULT_JSON.status, 32),
                gate: cleanString(m.AGENT_QA_RESULT_JSON.gate, 64),
                platform: cleanString(m.AGENT_QA_RESULT_JSON.platform, 32),
              }
            : null,
          markerCount: typeof m.markerCount === 'number' && m.markerCount >= 0 ? m.markerCount : 0,
          markerHash: typeof m.markerHash === 'string' ? m.markerHash.slice(0, 16) : '',
        }
      : null;
    const status = pickEnum(p.status, ALLOWED_LANE_STATUSES);
    return {
      id: pickEnum(row.lane_id, ALLOWED_LANE_IDS),
      status,
      terminalStatus: pickEnum(p.terminalStatus, ALLOWED_LANE_STATUSES),
      taskSummary: compressSummary(p.lastSummary),
      lastCommit: safeShortCommit(p.lastCommit),
      updatedAt: lastSeenAt,
      lastSeenAt,
      lastStateChangeAt,
      lastEventType: typeof p.lastEventType === 'string' ? redactText(p.lastEventType, 64) : null,
      lastEventAt: typeof p.lastEventAt === 'string' ? p.lastEventAt : null,
      source: typeof p.source === 'string' ? p.source : null,
      lastMarkers,
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
  // Defensive: accept BOTH `generatedAt` (canonical bridge field) and
  // `updatedAt` (legacy / partial-merge SQL writes) as freshness
  // candidates. Whichever is newest wins. This guards against
  // bridge↔Worker field-name drift; the underlying bridge writes
  // `payload.generatedAt` (scripts/bridge-snapshot-lanes.sh line 843
  // for work_status, line 875+ for lanes).
  const workValue = work as Record<string, unknown> | null;
  const buildValue = build as Record<string, unknown> | null;
  const updatedAt = latestIsoTimestamp([
    typeof workValue?.generatedAt === 'string' ? (workValue.generatedAt as string) : null,
    typeof workValue?.updatedAt === 'string' ? (workValue.updatedAt as string) : null,
    typeof buildValue?.generatedAt === 'string' ? (buildValue.generatedAt as string) : null,
    typeof buildValue?.updatedAt === 'string' ? (buildValue.updatedAt as string) : null,
    ...agentRows.map((g) => g.updatedAt),
  ]);
  const nowMs = Date.now();
  const freshness = computeFreshness(updatedAt, true, nowMs);
  const agents = agentRows.map((agent) => {
    const heartbeat = computeLaneHeartbeat(agent.status, agent.lastSeenAt, nowMs);
    const effectiveStatus = effectiveAgentStatusForFreshness(agent.status, freshness, heartbeat);
    const terminalStatus = agent.terminalStatus === 'unknown' ? agent.status : agent.terminalStatus;
    const terminalDisagreement = effectiveStatus !== agent.status || terminalStatus !== agent.status;
    return {
      ...agent,
      status: effectiveStatus,
      reportedStatus: agent.status,
      staleDowngraded: effectiveStatus !== agent.status,
      heartbeat,
      terminal: {
        status: terminalStatus,
        disagreement: terminalDisagreement,
        reason: terminalDisagreement
          ? (effectiveStatus !== agent.status ? 'cached_status_downgraded_by_stale_heartbeat' : 'terminal_status_differs_from_cached_status')
          : 'none',
      },
    };
  });

  const branchRe = /^[A-Za-z0-9._\-/]{1,80}$/;
  const branch = work?.repoStatus?.branch && branchRe.test(work.repoStatus.branch) ? work.repoStatus.branch : null;
  const head = safeShortCommit(work?.repoStatus?.head);
  const latestQaGate = buildPublicQaGate(handoff?.agentQaResult ?? null);
  const actionLedger = buildPublicActionLedgerSummary(handoff?.actionLedger ?? null);
  const handoffValue = handoff as Record<string, unknown> | null;
  const buildAuditUpdatedAt = latestIsoTimestamp([
    typeof buildValue?.generatedAt === 'string' ? (buildValue.generatedAt as string) : null,
    typeof buildValue?.updatedAt === 'string' ? (buildValue.updatedAt as string) : null,
    typeof handoffValue?.generatedAt === 'string' ? (handoffValue.generatedAt as string) : null,
    typeof handoffValue?.updatedAt === 'string' ? (handoffValue.updatedAt as string) : null,
  ]);
  const buildAuditLongRunning = build?.longRunning === true || handoff?.longRunning === true;
  const buildAuditFreshness = computeFreshnessWithWindow(
    buildAuditUpdatedAt,
    true,
    buildAuditLongRunning ? 24 * 60 * 60 * 1000 : BUILD_AUDIT_STALE_MS_V2,
    nowMs,
  );

  const haveAnyRow = work !== null || (lanes !== null && lanes.length > 0) || build !== null || handoff !== null;

  return {
    schemaVersion: 1,
    generatedAt,
    source: haveAnyRow ? 'supabase' as const : 'placeholder' as const,
    freshness,
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
      buildAuditFreshness,
      buildAuditLongRunning,
    },
    latestQaGate,
    actionLedger,
    safety: safetyBaseline,
  };
}

function buildPublicActionLedgerSummary(ledger: unknown): unknown | null {
  if (!ledger || typeof ledger !== 'object') return null;
  const value = ledger as Record<string, unknown>;
  const summary = value.summary && typeof value.summary === 'object'
    ? value.summary as Record<string, unknown>
    : {};
  const next = summary.nextPendingAction && typeof summary.nextPendingAction === 'object'
    ? summary.nextPendingAction as Record<string, unknown>
    : null;
  const priorities = Array.isArray(value.currentPriorityOrder)
    ? value.currentPriorityOrder.slice(0, 5).map((item) => {
        const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
        return {
          rank: typeof row.rank === 'number' ? row.rank : null,
          id: typeof row.id === 'string' ? row.id.slice(0, 80) : null,
          title: typeof row.title === 'string' ? row.title.slice(0, 140) : null,
          status: typeof row.status === 'string' ? row.status.slice(0, 60) : null,
        };
      }).filter((item) => item.id || item.title)
    : [];

  return {
    schemaVersion: 1,
    generatedAt: typeof value.generatedAt === 'string' ? value.generatedAt : null,
    pendingCount: typeof summary.pendingCount === 'number' ? summary.pendingCount : 0,
    activeCount: typeof summary.activeCount === 'number' ? summary.activeCount : 0,
    blockedCount: typeof summary.blockedCount === 'number' ? summary.blockedCount : 0,
    voidedCount: typeof summary.voidedCount === 'number' ? summary.voidedCount : 0,
    nextPendingAction: next
      ? {
          id: typeof next.id === 'string' ? next.id.slice(0, 80) : null,
          owner: typeof next.owner === 'string' ? next.owner.slice(0, 60) : null,
          targetWorkerOrPerson: typeof next.targetWorkerOrPerson === 'string' ? next.targetWorkerOrPerson.slice(0, 60) : null,
          lane: typeof next.lane === 'string' ? next.lane.slice(0, 100) : null,
          status: typeof next.status === 'string' ? next.status.slice(0, 40) : null,
          priority: typeof next.priority === 'string' ? next.priority.slice(0, 20) : null,
          actionText: typeof next.actionText === 'string' ? next.actionText.slice(0, 220) : null,
          triggerCondition: typeof next.triggerCondition === 'string' ? next.triggerCondition.slice(0, 220) : null,
        }
      : null,
    topPriorities: priorities,
    publicSafe: true,
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
    const list = withNativeIphoneAutomationPriority(await proxyWebsiteCall('list_pending_suggestions', {}));
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

export async function buildMobileLaneOverview(env: Env): Promise<unknown> {
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

export async function buildMobileBuildOverview(env: Env): Promise<unknown> {
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

export async function buildIntegrationsOverview(env: Env): Promise<unknown> {
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

export async function buildHandoffLatest(env: Env): Promise<unknown> {
  const adapter = getSupabaseAdapter(env);
  const generatedAt = new Date().toISOString();
  const entries: Array<{ source: 'mobile' | 'website'; generatedAt: string | null; summary: string; manualStepsCount: number | null }> = [];

  if (adapter.configured) {
    const payload = await adapter.fetchSingleRowPayload('connector_handoff') as {
      generatedAt?: string;
      latestClaudePrompt?: string | null;
      latestCodexPrompt?: string | null;
      manualSteps?: unknown[];
      actionLedger?: { summary?: { pendingCount?: unknown; activeCount?: unknown; blockedCount?: unknown } };
    } | null;
    if (payload) {
      const ledger = payload.actionLedger?.summary ?? {};
      const pending = typeof ledger.pendingCount === 'number' ? ledger.pendingCount : null;
      const active = typeof ledger.activeCount === 'number' ? ledger.activeCount : null;
      const blocked = typeof ledger.blockedCount === 'number' ? ledger.blockedCount : null;
      const ledgerSuffix = pending === null
        ? ''
        : ` actions pending=${pending} active=${active ?? 0} blocked=${blocked ?? 0}`;
      entries.push({
        source: 'mobile',
        generatedAt: typeof payload.generatedAt === 'string' ? payload.generatedAt : null,
        summary: `mobile bridge handoff — claude=${payload.latestClaudePrompt ?? '—'} codex=${payload.latestCodexPrompt ?? '—'}${ledgerSuffix}`.slice(0, 200),
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

async function buildQaListResults(env: Env): Promise<unknown> {
  const latest = await buildQaLatestResult(env) as {
    schemaVersion?: number;
    generatedAt?: string;
    source?: unknown;
    freshness?: unknown;
    latestQaGate?: unknown;
  };
  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    source: latest.source ?? 'placeholder',
    freshness: latest.freshness,
    results: latest.latestQaGate ? [latest.latestQaGate] : [],
    resultCount: latest.latestQaGate ? 1 : 0,
    note: 'Current bridge stores the latest Agent QA result only; historical QA result table is not enabled yet.',
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
    payload: sanitizeQaResult(full.payload?.agentQaResult ?? null, 'admin'),
  };
}

async function buildReleaseGate(env: Env): Promise<unknown> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      source: 'placeholder' as const,
      freshness: computeFreshness(null, false),
      current: { iosBuildNumber: null, androidVersionCode: null },
      target: { iosBuildNumber: '19', androidVersionCode: 18, appVersion: '0.1.0' },
      qaState: null,
      buildAllowed: { ios: false, android: false },
      reason: 'Supabase bridge is not configured.',
      publicSafe: true,
    };
  }
  const [build, handoff] = await Promise.all([
    adapter.fetchSingleRowPayload('connector_build_status') as Promise<{
      generatedAt?: string;
      android?: { versionCode?: number | null; playStatus?: string | null; playTrack?: string | null };
      ios?: { buildNumber?: string | null; testflightStatus?: string | null };
    } | null>,
    adapter.fetchSingleRowPayload('connector_handoff') as Promise<{ generatedAt?: string; agentQaResult?: unknown } | null>,
  ]);
  const latestQaGate = buildPublicQaGate(handoff?.agentQaResult ?? null) as {
    status?: string;
    gate?: string;
    platform?: string;
    freshness?: { isStale?: boolean; staleReason?: string };
    releaseGate?: { newTestFlightAllowed?: boolean; newAndroidBuildAllowed?: boolean; reason?: string };
  } | null;
  const target = currentQaBuildTargets(handoff?.agentQaResult ?? null);
  const updatedAt = typeof handoff?.generatedAt === 'string' ? handoff.generatedAt : typeof build?.generatedAt === 'string' ? build.generatedAt : null;
  const reason = latestQaGate?.releaseGate?.reason ?? 'No Agent QA result is available; build gates remain blocked.';
  return {
    schemaVersion: 1,
    generatedAt,
    source: build || handoff ? ('supabase' as const) : ('placeholder' as const),
    freshness: computeFreshness(updatedAt, true),
    current: {
      iosBuildNumber: typeof build?.ios?.buildNumber === 'string' ? build.ios.buildNumber : null,
      iosStatus: typeof build?.ios?.testflightStatus === 'string' ? build.ios.testflightStatus : null,
      androidVersionCode: typeof build?.android?.versionCode === 'number' ? build.android.versionCode : null,
      androidStatus: typeof build?.android?.playStatus === 'string' ? build.android.playStatus : null,
      androidTrack: typeof build?.android?.playTrack === 'string' ? build.android.playTrack : null,
    },
    target,
    qaState: latestQaGate
      ? {
          status: latestQaGate.status ?? 'unknown',
          gate: latestQaGate.gate ?? 'general',
          platform: latestQaGate.platform ?? 'repo',
          freshness: latestQaGate.freshness ?? null,
        }
      : null,
    buildAllowed: {
      ios: latestQaGate?.releaseGate?.newTestFlightAllowed === true,
      android: latestQaGate?.releaseGate?.newAndroidBuildAllowed === true,
    },
    reason,
    commands: {
      iosQaBuild: 'cd apps/mobile && npx eas-cli build --platform ios --profile production',
      iosSubmit: 'cd apps/mobile && npx eas-cli submit --platform ios --profile production --latest',
      androidQaBuild: 'cd apps/mobile && npx eas-cli build --platform android --profile production --auto-submit',
    },
    publicSafe: true,
  };
}

async function buildMobileBuildReadiness(env: Env): Promise<unknown> {
  const gate = await buildReleaseGate(env);
  const qa = await buildMobileAgentQaResult(env);
  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    releaseGate: gate,
    latestAgentQaResult: (qa as { payload?: unknown }).payload ?? null,
    installedDeviceGateRule: 'repo_only/stale/blocked/fail/partial QA does not clear installed-device QA gates; pass must match target platform/build.',
    safeToRunBuild: false,
    safeToRunBuildReason: 'No EAS build may start until Agent confirms worthwhile installed-device testing and Aaron explicitly approves.',
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
  const generatedAt = new Date().toISOString();
  if (!adapter.configured) {
    return {
      schemaVersion: 1,
      generatedAt,
      source: 'placeholder' as const,
      freshness: computeFreshness(null, false),
      lanes: [],
    };
  }
  const [rows, terminalEntries] = await Promise.all([
    adapter.fetchCoderLaneRows(),
    adapter.fetchTerminalEntries(50),
  ]);
  const latestTerminalByLane = new Map<string, {
    summary?: unknown;
    verification?: unknown;
    nextAction?: unknown;
    exitCode?: unknown;
    at?: unknown;
  }>();
  for (const entry of (terminalEntries ?? []) as Array<Record<string, unknown>>) {
    const laneId = typeof entry.laneId === 'string' ? entry.laneId : '';
    if (laneId && !latestTerminalByLane.has(laneId)) latestTerminalByLane.set(laneId, entry);
  }
  const lanes = (rows ?? []).map((r) => {
    const p = (r.payload ?? {}) as Record<string, unknown>;
    const laneId = typeof p.laneId === 'string' ? p.laneId : r.lane_id;
    const terminal = latestTerminalByLane.get(laneId) ?? null;
    const verification = redactText(terminal?.verification, 500);
    const exitCode = typeof terminal?.exitCode === 'number' ? terminal.exitCode : null;
    const status = typeof p.status === 'string' ? p.status : 'unknown';
    return {
      agentId: laneId,
      status,
      taskBundle: redactText(p.currentPromptId ?? p.lastPromptId, 120),
      taskSummary: redactText(p.lastSummary, 1200),
      filesChangedSummary: Array.isArray(p.dirtyFiles) ? `${p.dirtyFiles.length} dirty file(s)` : '0 dirty file(s)',
      testsRun: verification,
      testResult: exitCode === 0
        ? 'pass'
        : exitCode === null
          ? (verification ? 'reported' : 'unknown')
          : 'fail',
      blockers: status === 'blocked' ? redactText(p.lastSummary, 500) : null,
      nextExactStep: redactText(p.nextPrompt ?? terminal?.nextAction, 500),
      lastCommit: safeShortCommit(p.lastCommit),
      updatedAt: safeIso(p.lastSeenAt),
      terminalSummary: redactText(terminal?.summary, 800),
      terminalUpdatedAt: safeIso(terminal?.at),
      rawTerminalLogsWithheld: true,
      dirtyFilePathsWithheld: true,
    };
  });
  const updatedAt = lanes
    .map((lane) => lane.updatedAt)
    .filter((value): value is string => typeof value === 'string')
    .sort()
    .slice(-1)[0] ?? null;
  return {
    schemaVersion: 1,
    generatedAt,
    source: lanes.length > 0 ? ('supabase' as const) : ('placeholder' as const),
    freshness: computeFreshness(updatedAt, true),
    lanes,
  };
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

/**
 * Each tool is tagged with a surface so /mcp/v2 can stay under
 * ChatGPT's tool-picker cap (~30 tools) while terminal/coder
 * callers continue to reach admin and website-proxy tools at
 * dedicated paths.
 *
 *   - 'core'    → exposed at /mcp/v2 only. Public-safe + the
 *                 admin write tools (token-gated; ChatGPT lists
 *                 them but cannot call them without a Bearer
 *                 token, which keeps the surface ≤25 tools).
 *   - 'admin'   → exposed at /mcp/v2/admin only. Includes all
 *                 admin-token full-payload reads plus the
 *                 public-safe extras (qa.*, release.get_gate,
 *                 mobile.get_repo_overview, project.get_overview,
 *                 project.list_priorities) that aren't required
 *                 for the ChatGPT-friendly core surface.
 *
 * The website.* runtime-merged proxy is gated separately by URL
 * path (handled in dispatchToolCall + listAllTools); /mcp/v2
 * never includes website.*. /mcp/v2/website is the dedicated
 * surface for those 25 proxied tools.
 */
type ToolSurface = 'core' | 'admin';

interface LocalToolEntry {
  name: string;
  description: string;
  inputSchema: unknown;
  auth: 'public' | 'admin';
  surface: ToolSurface;
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

async function buildProjectPing(_env: Env): Promise<unknown> {
  return {
    schemaVersion: 1,
    ok: true,
    serverInfo: SERVER_INFO,
    surface: 'core' as const,
    transport: 'streamable-http' as const,
    protocolVersion: PROTOCOL_VERSION,
    auth: 'no_auth' as const,
    publicSafe: true,
    timestamp: new Date().toISOString(),
    note: 'project.ping is a tiny diagnostic — no Supabase fetch, no proxies. If a client can call this tool but no other tool, the issue is upstream (Supabase / website MCP), not the MCP transport.',
  };
}

const LOCAL_TOOLS: readonly LocalToolEntry[] = [
  {
    name: 'project.ping',
    description: 'Tiny zero-dependency diagnostic. Returns serverInfo + protocolVersion + transport + timestamp + a publicSafe flag. Use this from a ChatGPT custom connector or Anthropic Agent first to verify the MCP transport is reachable; if it succeeds but project.get_current_state fails, the issue is the Supabase mirror, not MCP. Public-safe; no auth.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
    build: buildProjectPing,
  },
  {
    name: 'project.get_overview',
    description: 'Cross-project aggregate: top mobile priority, open manual-steps count, website pending suggestions count. No free text > 120 chars. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'admin',
    build: buildProjectOverview,
  },
  {
    name: 'project.get_current_state',
    description: 'Canonical "what is the team working on right now" snapshot. Composes priority / blocker / next action + per-lane (claude / codex) status + sanitised task summaries (≤140 char) + Android v + iOS Build state + freshness flag. Public-safe; the source enum + staleReason fields make it explicit when data is older than the 10-min freshness window. Use this from ChatGPT instead of the website MCP when you want current dev state.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
    build: buildProjectCurrentState,
  },
  {
    name: 'project.get_work_status',
    description: 'Sanitised work status — currentPriority, currentBlocker, nextAction (each ≤280 char) plus a blocked boolean. No raw text fields beyond those three. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
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
    surface: 'core',
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
    surface: 'admin',
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
    surface: 'admin',
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
    surface: 'admin',
    build: submitProjectPrioritySuggestion,
  },
  {
    name: 'project.get_operating_rules',
    description: 'Returns the canonical 23 operating rules every coder / agent / consumer must follow (audit→bundles, parallel lanes, no stopping at one patch, re-audit on implementation-complete, Agent-confirmed gate, EAS build cost control, no "fully done" without Aaron, provisional health claims, repo docs as source of truth, MCP-first start, coders run all laptop commands, clear-steps automate-first, parallel priorities stay active, no-idle dependency, no delayed instruction chains, deferred prompt/action backlog hygiene, action ledger until evidence clears, coordinator-fed idle lanes, all-idle notification, human-approval push gate, AI spend gate, deep research offload + artifact cache). Stable rule IDs 1..23 + titles + bodies. Mirror of docs/OPERATING_RULES.md. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
    build: async () => buildOperatingRulesPayload(),
  },
  {
    name: 'project.list_priorities',
    description: 'Top backlog items across the active mobile-app project. Each entry: source / rank / title / status. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'admin',
    build: buildProjectListPriorities,
  },
  {
    name: 'mobile.get_lane_overview',
    description: 'Coder lane counts by status enum. No per-lane text. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
    build: buildMobileLaneOverview,
  },
  {
    name: 'mobile.get_build_overview',
    description: 'Latest paired-build status enums + Android versionCode + iOS buildNumber. No EAS / submission UUIDs. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
    build: buildMobileBuildOverview,
  },
  {
    name: 'mobile.get_repo_overview',
    description: 'Branch + short HEAD SHA. Both already public on GitHub. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'admin',
    build: buildMobileRepoOverview,
  },
  {
    name: 'mobile.get_control_centre',
    description: 'Full ControlCentreSnapshot (priority, blocker, lanes, build, repo, manualSteps, topBacklog, suggestionCounts, promptLibrary, safety). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: buildMobileControlCentre,
  },
  {
    name: 'mobile.get_coder_lanes',
    description: 'Full coder-lanes payload — per-lane summaries with text, prompts, dirtyFiles. Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: buildMobileCoderLanes,
  },
  {
    name: 'mobile.get_work_status',
    description: 'Full WorkStatus payload (priority, blocker, liveStatus, repoStatus, nextAction). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: (env) => buildMobileFullSingle(env, 'connector_work_status'),
  },
  {
    name: 'mobile.get_build_status',
    description: 'Full BuildStatus payload (Android + iOS release rows including IDs). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: (env) => buildMobileFullSingle(env, 'connector_build_status'),
  },
  {
    name: 'mobile.get_build_readiness',
    description: 'Admin-gated release readiness drill-down: latest Agent QA result, release gate, target build commands, and why builds are or are not allowed.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: buildMobileBuildReadiness,
  },
  {
    name: 'mobile.get_handoff',
    description: 'Full Handoff payload (manualSteps text, doNotTouch, safeToBuild). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: (env) => buildMobileFullSingle(env, 'connector_handoff'),
  },
  {
    name: 'mobile.get_terminal_summary',
    description: 'TerminalSummary entries (≤50, most recent first, full text). Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: buildMobileTerminalSummary,
  },
  {
    name: 'integrations.get_overview',
    description: 'Per-platform exposure of Apple Health (iOS only) / Health Connect (Android only) / WHOOP / Polar. Aggregates only. No per-user data. Public-safe.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
    build: buildIntegrationsOverview,
  },
  {
    name: 'handoff.get_latest',
    description: 'Latest handoff entries from both projects, each tagged source: mobile|website. Public-safe summary; admin token unlocks richer fields.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'core',
    build: buildHandoffLatest,
  },
  {
    name: 'qa.get_latest_result',
    description: 'Latest public-safe Agent QA gate summary. Shows repo-only vs installed-device QA status, tested platform/build, and whether TestFlight/Internal QA build is allowed. No screenshots, private details, or raw logs.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'admin',
    build: buildQaLatestResult,
  },
  {
    name: 'qa.list_results',
    description: 'Public-safe Agent QA result list. Currently returns the latest bridge result only; historical storage is not enabled yet.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'admin',
    build: buildQaListResults,
  },
  {
    name: 'release.get_gate',
    description: 'Public-safe release gate detail: current installed build, target QA build, latest QA state, build-allowed booleans, and exact reason. No secrets or raw logs.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'public',
    surface: 'admin',
    build: buildReleaseGate,
  },
  {
    name: 'mobile.get_agent_qa_result',
    description: 'Full latest Agent QA result carried by connector_handoff.agentQaResult. Admin token required.',
    inputSchema: { type: 'object', properties: {}, required: [] },
    auth: 'admin',
    surface: 'admin',
    build: buildMobileAgentQaResult,
  },
];

const LOCAL_BY_NAME = new Map(LOCAL_TOOLS.map((t) => [t.name, t] as const));

/** /mcp/v2 surface gate. */
type V2Surface = 'core' | 'admin' | 'website';

// ── JSON-RPC dispatch ────────────────────────────────────────────────

/**
 * Return the tools advertised on a given /mcp/v2 surface.
 *
 *   - 'core'    → 8 LOCAL_TOOLS tagged surface: 'core'.
 *                 Stays under ChatGPT's tool-picker cap.
 *   - 'admin'   → 17 LOCAL_TOOLS tagged surface: 'admin'.
 *                 Includes admin-token reads + non-core public-safe
 *                 extras (qa.*, release.get_gate, project.get_overview,
 *                 etc). Terminal/coder use.
 *   - 'website' → 25 website.* proxy tools fetched from
 *                 mcp.lauburugrapplingmap.com/mcp at request time.
 */
async function listToolsForSurface(
  surface: V2Surface,
): Promise<Array<{ name: string; description: string; inputSchema: unknown }>> {
  if (surface === 'website') {
    return proxyWebsiteToolsList();
  }
  return LOCAL_TOOLS
    .filter((t) => t.surface === surface)
    .map(({ name, description, inputSchema }) => ({ name, description, inputSchema }));
}

async function dispatchToolCall(
  env: Env,
  request: Request,
  name: string,
  args: unknown,
  surface: V2Surface,
): Promise<unknown> {
  if (surface === 'website') {
    if (!name.startsWith('website.')) return null;
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
  if (tool.surface !== surface) return null;
  if (tool.auth === 'admin' && !tokenAuthorised(request, env)) {
    return adminGateError();
  }
  const payload = await tool.build(env, args);
  return {
    content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
    isError: false,
  };
}

function instructionsForSurface(surface: V2Surface): string {
  switch (surface) {
    case 'core':
      return 'Lauburu / GrapplingMap MCP — core surface. Eight ChatGPT-friendly tools: project.get_current_state, project.get_operating_rules, project.get_work_status, project.update_work_status (admin), handoff.get_latest, integrations.get_overview, mobile.get_lane_overview, mobile.get_build_overview. Public-safe except project.update_work_status which requires x-athlete-memory-token or Authorization: Bearer. Admin reads (mobile.get_<full>, qa.*, release.get_gate, project.get_overview/list_priorities) are at /mcp/v2/admin. Website-project tools are at /mcp/v2/website.';
    case 'admin':
      return 'Lauburu / GrapplingMap MCP — admin surface. Admin-token-gated full payloads (mobile.get_control_centre / coder_lanes / work_status / build_status / build_readiness / handoff / terminal_summary / agent_qa_result, project.submit_priority_suggestion, alias submit_priority_suggestion + update_work_status) plus non-core public-safe tools (project.get_overview, project.list_priorities, mobile.get_repo_overview, qa.*, release.get_gate). ChatGPT-friendly core is at /mcp/v2; website-project tools at /mcp/v2/website.';
    case 'website':
      return 'Lauburu / GrapplingMap MCP — website-project proxy. Forwards JSON-RPC tools/call to mcp.lauburugrapplingmap.com/mcp (the website project MCP server). Tool list and schemas are fetched at request time. Twenty-five tools: jubjub.*, suggestions.*, automation.*, work-status.*, etc.';
  }
}

async function handleRpcRequest(req: JsonRpcRequest, env: Env, request: Request, surface: V2Surface): Promise<JsonRpcResponse | null> {
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
        serverInfo: { ...SERVER_INFO, surface },
        instructions: instructionsForSurface(surface),
      });
    case 'notifications/initialized':
    case 'notifications/cancelled':
    case 'notifications/progress':
      return null;
    case 'ping':
      return rpcResult(id, {});
    case 'tools/list': {
      const tools = await listToolsForSurface(surface);
      return rpcResult(id, { tools });
    }
    case 'tools/call': {
      const params = (req.params as { name?: string; arguments?: unknown }) ?? {};
      const name = params.name ?? '';
      const result = await dispatchToolCall(env, request, name, params.arguments, surface);
      if (result === null) return rpcError(id, -32602, `Unknown tool for ${surface} surface: ${name || '<missing>'}`);
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

export async function handleMcpV2(request: Request, env: Env, surface: V2Surface = 'core'): Promise<Response> {
  if (request.method === 'OPTIONS') {
    return optionsResponse();
  }

  if (request.method === 'GET') {
    const tools = await listToolsForSurface(surface);
    return jsonResponse({
      ok: true,
      protocolVersion: PROTOCOL_VERSION,
      serverInfo: { ...SERVER_INFO, surface },
      transport: 'streamable-http',
      auth: {
        public: 'no auth required for public-safe tools',
        admin: 'Authorization: Bearer <ATHLETE_MEMORY_API_TOKEN> OR x-athlete-memory-token header',
      },
      surface,
      tools: tools.map((t) => ({ name: t.name, description: (t.description ?? '').slice(0, 160) })),
      hint: surface === 'core'
        ? 'POST JSON-RPC 2.0 here. ChatGPT-friendly core surface (≤25 tools). Admin/full at /mcp/v2/admin; website-project tools at /mcp/v2/website.'
        : surface === 'admin'
          ? 'POST JSON-RPC 2.0 here. Admin surface — full payload reads + admin write tools. Public-safe extras live here too. ChatGPT-friendly core at /mcp/v2.'
          : 'POST JSON-RPC 2.0 here. Website-project proxy — forwards to mcp.lauburugrapplingmap.com/mcp.',
    });
  }

  if (request.method !== 'POST') {
    return jsonResponse(rpcError(null, -32600, 'POST or GET only.'), { status: 405, headers: { allow: 'GET, POST' } });
  }

  let body: unknown;
  try { body = await request.json(); } catch { return jsonResponse(rpcError(null, -32700, 'Parse error'), { status: 400 }); }

  if (Array.isArray(body)) {
    const responses = await Promise.all(body.map((req) => handleRpcRequest(req as JsonRpcRequest, env, request, surface)));
    const filtered = responses.filter((r): r is JsonRpcResponse => r !== null);
    if (filtered.length === 0) return acceptedResponse();
    return negotiated(request, filtered);
  }
  const response = await handleRpcRequest(body as JsonRpcRequest, env, request, surface);
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
      'qa.list_results',
      'release.get_gate',
    ],
  });
}
