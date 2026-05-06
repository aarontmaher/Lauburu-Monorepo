/**
 * Lauburu MCP / app-dev-centre Cloudflare Worker.
 *
 * Status today: ACTIVE — this Worker is the live MCP / control-centre
 * surface. The legacy Railway backend at
 * `https://lauburu-ai-backend-production.up.railway.app` is
 * DEPRECATED (Aaron cannot maintain Railway billing) and the Worker
 * never proxies through it. RAILWAY_FALLBACK_URL is retained only
 * as a legacy reference value for documentation responses; nothing
 * relies on it being reachable.
 *
 * Supabase is the durable state layer. The adapter in
 * `./supabase.ts` reports configuration state; once the connector
 * tables in `docs/CONNECTOR_SUPABASE_SCHEMA.md` exist, the route
 * helpers below switch from placeholder payloads to live reads.
 *
 * Endpoints exposed:
 *   GET /health
 *   GET /status
 *   GET /mcp/health
 *   GET /app-dev-centre/status
 *   GET /handoff
 *   GET /automation-state
 *   GET /pending-suggestions
 *
 * Auth model:
 *   Read endpoints return `mode: 'repo-only'` metadata until
 *   Supabase env is set. They never expose secrets, never
 *   surface raw athlete health values, and never proxy
 *   `/v1/internal/*` server-to-server routes from the legacy
 *   Railway backend (those stay strictly server-to-server).
 *
 * No write endpoints in the starter — `POST /suggestions` is
 * commented out until an authenticated write path exists.
 */

import type { Env } from './worker-env';
import {
  CONNECTOR_SCHEMA_REQUIREMENTS,
  getSupabaseAdapter,
  type ConnectorRouteKey,
} from './supabase';
import { handleMcp } from './mcp';
import { handleMcpPublic } from './mcp-public';
import { buildControlCentreSnapshot } from './control-centre';

interface ConnectorMeta {
  generatedAt: string;
  provider: 'cloudflare-workers';
  mode: string;
  workerName: string;
  supabaseConfigured: boolean;
  /** Always false — Railway is deprecated, never proxied. */
  railwayRequired: false;
  /** Always true — flag retained so consumers can assert on it. */
  railwayDeprecated: true;
  /** Reference URL only; the Worker never calls it. */
  legacyRailwayUrl: string | null;
}

function buildMeta(env: Env): ConnectorMeta {
  const adapter = getSupabaseAdapter(env);
  return {
    generatedAt: new Date().toISOString(),
    provider: 'cloudflare-workers',
    mode: env.WORKER_MODE ?? 'unknown',
    workerName: 'lauburu-mcp',
    supabaseConfigured: adapter.configured === true,
    railwayRequired: false,
    railwayDeprecated: true,
    legacyRailwayUrl: env.RAILWAY_FALLBACK_URL ?? null,
  };
}

/**
 * Placeholder data-source descriptor used by the placeholder
 * builders. Always reports `source: 'placeholder'`. When the
 * adapter is configured but the table is empty, reason is
 * `'table_empty'`; when the adapter itself is not configured,
 * reason mirrors the adapter's failure mode.
 */
function dataSourceFor(env: Env, route: ConnectorRouteKey) {
  const adapter = getSupabaseAdapter(env);
  const schema = CONNECTOR_SCHEMA_REQUIREMENTS[route];
  if (adapter.configured) {
    return {
      source: 'placeholder' as const,
      reason: 'table_empty' as const,
      message:
        `Supabase env configured but ${schema.table} returned no rows. Bridge upsert needed before this route serves live data.`,
      schemaRequired: schema,
    };
  }
  return {
    source: 'placeholder' as const,
    reason: adapter.reason,
    message: adapter.message,
    schemaRequired: schema,
  };
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body, null, 2), {
    ...init,
    headers: {
      'content-type': 'application/json',
      'cache-control': 'no-store',
      ...(init.headers ?? {}),
    },
  });
}

function notFound(): Response {
  return jsonResponse({ ok: false, error: 'Route not found.' }, { status: 404 });
}

function requireAdminToken(req: Request, env: Env): { ok: boolean; reason?: string } {
  const expected = env.ATHLETE_MEMORY_API_TOKEN ?? '';
  if (expected.length === 0) {
    return {
      ok: false,
      reason:
        'Admin token not configured on this Worker — set ATHLETE_MEMORY_API_TOKEN via `wrangler secret put`.',
    };
  }
  const presented = req.headers.get('x-athlete-memory-token') ?? '';
  if (presented !== expected) return { ok: false, reason: 'Forbidden admin access.' };
  return { ok: true };
}

// ── Connector payload shapes (mirror chat-app/src/server/types/connector.ts) ──

const CONNECTOR_SCHEMA_VERSION = 1 as const;

async function tryReadSingleRowPayload(
  env: Env,
  route: ConnectorRouteKey,
  table: string,
): Promise<{ source: 'supabase'; payload: unknown } | { source: 'placeholder'; descriptor: ReturnType<typeof dataSourceFor> }> {
  const adapter = getSupabaseAdapter(env);
  if (adapter.configured) {
    const payload = await adapter.fetchSingleRowPayload(table);
    if (payload && typeof payload === 'object') {
      return { source: 'supabase', payload };
    }
  }
  return { source: 'placeholder', descriptor: dataSourceFor(env, route) };
}

function placeholderWorkStatus(env: Env) {
  const generatedAt = new Date().toISOString();
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt,
    dataSource: dataSourceFor(env, 'work_status'),
    currentPriority:
      'Cloudflare Worker is the active MCP connector surface; Railway deprecated; Supabase schema next.',
    currentBlocker:
      'connector_* Supabase tables not created yet — see docs/CONNECTOR_SUPABASE_SCHEMA.md.',
    liveStatus: {
      androidVersionCode: 17,
      iosBuildNumber: '18',
      androidPlayTrack: 'internal' as const,
      iosTestflightGroup: 'Team (Expo)',
      lastRailwayDeployAt: null,
      cloudflareWorkerDeployed: true,
    },
    repoStatus: {
      head: 'unknown',
      branch: 'main',
      dirtyFileCount: 0,
      untrackedFileCount: 0,
      lastCommitAt: generatedAt,
      lastCommitMessage: 'unknown until Supabase reads land',
    },
    nextAction:
      'Create connector_* Supabase tables per docs/CONNECTOR_SUPABASE_SCHEMA.md, set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY secrets on the Worker, redeploy.',
  };
}

function placeholderCoderLanes(env: Env) {
  const generatedAt = new Date().toISOString();
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt,
    dataSource: dataSourceFor(env, 'coder_lanes'),
    lanes: [
      {
        laneId: 'claude' as const,
        status: 'idle' as const,
        lastSeenAt: generatedAt,
        currentPromptId: null,
        lastPromptId: 'CLAUDE-CLOUDFLARE-SUPABASE-CUTOVER-PRIORITY-01',
        lastSummary:
          'Claude lane parked after Supabase-cutover scaffold. Awaiting next owner-reviewed handoff.',
        lastCommit: null,
        lastTypecheckResult: null,
        dirtyFiles: [],
        nextPrompt: null,
      },
      {
        laneId: 'codex' as const,
        status: 'idle' as const,
        lastSeenAt: generatedAt,
        currentPromptId: null,
        lastPromptId: 'CODEX-BACKEND-API-AI-IMPLEMENTATION-01',
        lastSummary:
          'Codex completed b6fe1ad (chat-app routes). Cloudflare mirror landed by Claude. Awaiting next prompt.',
        lastCommit: null,
        lastTypecheckResult: 'pass' as const,
        dirtyFiles: [],
        nextPrompt: null,
      },
    ],
  };
}

function placeholderBuildStatus(env: Env) {
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
    dataSource: dataSourceFor(env, 'build_status'),
    android: {
      versionCode: 17,
      appVersion: '0.1.0',
      githubRunId: '25417977756',
      githubStatus: 'success' as const,
      easBuildId: '92778b10-7023-4ce6-b665-398069fa9d28',
      easBuildUrl: null,
      playSubmissionId: '94cee638-97b3-4fcd-a2ba-5834b2d3be20',
      playStatus: 'submitted_completed' as const,
      playTrack: 'internal' as const,
    },
    ios: {
      buildNumber: '18',
      appVersion: '0.1.0',
      githubRunId: '25417981099',
      githubStatus: 'success' as const,
      easBuildId: 'b05edd9a-0a16-42a2-9bf6-c04f95b2feea',
      easBuildUrl: null,
      testflightSubmissionId: 'badb173d-cf75-49ae-8be4-3d2e79088d4d',
      testflightStatus: 'uploaded_processing' as const,
      testflightGroup: 'Team (Expo)',
    },
  };
}

function placeholderHandoff(env: Env) {
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
    dataSource: dataSourceFor(env, 'handoff'),
    latestClaudePrompt: 'CLAUDE-CLOUDFLARE-SUPABASE-CUTOVER-PRIORITY-01',
    latestCodexPrompt: 'CODEX-BACKEND-API-AI-IMPLEMENTATION-01',
    manualSteps: [
      'Aaron: create connector_* Supabase tables per docs/CONNECTOR_SUPABASE_SCHEMA.md.',
      'Aaron: set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY secrets on the Worker via wrangler secret put.',
      'Aaron: keep build dispatch owner-tap only — connector cannot tap.',
    ],
    doNotTouch: [
      'grappling.opml',
      'apps/mobile/app.json',
      'apps/mobile/eas.json',
      '.github/workflows',
    ],
    safeToBuild: false,
    safeToBuildReason:
      'Connector cutover in flight; verify Worker live + bridge producer before next paired build.',
  };
}

// ── Inline two-pass redactor (mirrors chat-app redactTokenLikeSubstrings) ──
// Workers runtime can't import the chat-app code, so this is a small
// re-implementation matching docs/CONNECTOR_SANITIZATION_RULES.md.
// Pass 1 preserves labelled values (commit/sha/build/run_id/etc.) via
// sentinel tags; Pass 2 strikes token-shaped substrings; final swap
// restores the labelled values.

const PRESERVE_LABELS = new Set([
  'commit', 'commit_hash', 'sha', 'head', 'ref', 'branch', 'version',
  'build', 'build_number', 'version_code', 'tag', 'prompt_id', 'lane',
  'run_id', 'submission', 'eas_build', 'expo_build_id',
  'androidversioncode', 'iosbuildnumber', 'githubrunid', 'easbuildid',
  'playsubmissionid', 'testflightsubmissionid',
]);

const STRIKE_PATTERNS: RegExp[] = [
  /eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+/g, // JWTs
  /sk-[A-Za-z0-9_\-]{20,}/g,
  /ghp_[A-Za-z0-9]{30,}/g,
  /gho_[A-Za-z0-9]{30,}/g,
  /ghs_[A-Za-z0-9]{30,}/g,
  /whsec_[A-Za-z0-9]{20,}/g,
  /AKIA[0-9A-Z]{16}/g,
  /xox[abprs]-[A-Za-z0-9\-]{10,}/g,
];

function redactString(input: string): string {
  if (typeof input !== 'string' || input.length === 0) return input;
  // Pass 1: tag labelled values so Pass 2 doesn't strike them.
  const preserved: string[] = [];
  const labelRe = /(^|[^A-Za-z0-9_])([a-z_]+)(\s*[:=]\s*)([A-Za-z0-9.\-_]+)/g;
  let tagged = input.replace(labelRe, (full, lead, label: string, sep, value: string) => {
    if (!PRESERVE_LABELS.has(label.toLowerCase())) return full;
    const idx = preserved.length;
    preserved.push(value);
    return `${lead}${label}${sep}\u0000PRESERVE_${idx}\u0000`;
  });
  // Pass 2: strike token-shaped substrings outside sentinels.
  for (const re of STRIKE_PATTERNS) tagged = tagged.replace(re, '<redacted>');
  // Restore preserved values.
  tagged = tagged.replace(/\u0000PRESERVE_(\d+)\u0000/g, (_m, n) => preserved[Number(n)] ?? '');
  return tagged;
}

function applyConnectorRedaction<T>(payload: T): T {
  if (Array.isArray(payload)) {
    return payload.map((v) => applyConnectorRedaction(v)) as unknown as T;
  }
  if (payload !== null && typeof payload === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(payload as Record<string, unknown>)) {
      out[k] = applyConnectorRedaction(v);
    }
    return out as unknown as T;
  }
  if (typeof payload === 'string') return redactString(payload) as unknown as T;
  return payload;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '');

    // ── /mcp/public — public-safe preview MCP (no auth) ────────────────
    // Sanitised aggregate-only tool surface for ChatGPT custom
    // connectors that don't support API-key / Bearer auth in the UI.
    // Implementation in ./mcp-public.ts. Strict allowlist; no free
    // text, no paths, no prompts, no terminal logs.
    if (path === '/mcp/public') {
      return handleMcpPublic(request, env);
    }

    // ── /mcp — full-fidelity JSON-RPC 2.0 MCP server (admin-gated) ─────
    // Private read-only tool surface — every coder lane / handoff /
    // terminal summary detail. Implementation in ./mcp.ts. Auth via
    // x-athlete-memory-token OR Authorization: Bearer <token>.
    if (path === '/mcp') {
      return handleMcp(request, env);
    }

    // ── Public health check (no auth) ──────────────────────────────────
    if (request.method === 'GET' && (path === '' || path === '/' || path === '/health')) {
      return jsonResponse({
        ...buildMeta(env),
        ok: true,
        message: 'Lauburu MCP Cloudflare Worker — repo-only until deployed and verified.',
      });
    }

    // ── /status — public meta ──────────────────────────────────────────
    if (request.method === 'GET' && path === '/status') {
      return jsonResponse({
        ...buildMeta(env),
        ok: true,
        endpoints: [
          'GET /health',
          'GET /status',
          'GET /mcp (private full-fidelity MCP server info; POST for JSON-RPC 2.0)',
          'POST /mcp (private MCP — admin-token-gated; full coder lane / handoff / terminal data)',
          'GET /mcp/public (public-safe preview MCP server info; POST for JSON-RPC 2.0)',
          'POST /mcp/public (public-safe preview — sanitised aggregate overviews only, no auth required)',
          'GET /supabase/health',
          'GET /mcp/health',
          'GET /app-dev-centre/status',
          'GET /handoff',
          'GET /automation-state',
          'GET /pending-suggestions',
          'GET /api/work_status',
          'GET /api/coder_lanes',
          'GET /api/build_status',
          'GET /api/handoff',
          'GET /api/terminal_summary',
          'GET /api/control_centre',
        ],
      });
    }

    // ── /supabase/health ───────────────────────────────────────────────
    // Admin-gated probe of the Supabase adapter. Returns whether the
    // env is configured and, if so, the result of pinging
    // PostgREST `/rest/v1/`. Surfacing this separately keeps the MCP
    // routes terse while giving Aaron a single curl to verify the
    // Supabase wiring after a secret rotation.
    if (request.method === 'GET' && path === '/supabase/health') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      const adapter = getSupabaseAdapter(env);
      if (!adapter.configured) {
        return jsonResponse({
          ...buildMeta(env),
          supabase: {
            configured: false,
            reason: adapter.reason,
            message: adapter.message,
            schemaRequirements: CONNECTOR_SCHEMA_REQUIREMENTS,
          },
        });
      }
      const ping = await adapter.ping();
      return jsonResponse({
        ...buildMeta(env),
        supabase: {
          configured: true,
          host: adapter.config.url,
          ping,
        },
      });
    }

    // ── /mcp/health ────────────────────────────────────────────────────
    // Connector-shaped probe — same shape as Railway's
    // /api/athlete-memory/admin/work-status when wired.
    if (request.method === 'GET' && path === '/mcp/health') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse({
        ...buildMeta(env),
        mcp: {
          status: 'live-placeholder',
          notes:
            'Worker is the active MCP surface (Railway deprecated). Connector routes return placeholder payloads with `dataSource.schemaRequired` until the connector_* Supabase tables in docs/CONNECTOR_SUPABASE_SCHEMA.md are created and the SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY secrets are set.',
          targetEndpoints: ['get_work_status', 'get_release_status', 'get_health_source_status'],
        },
      });
    }

    // ── /app-dev-centre/status ─────────────────────────────────────────
    if (request.method === 'GET' && path === '/app-dev-centre/status') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse({
        ...buildMeta(env),
        appDevCentre: {
          status: 'live-placeholder',
          notes:
            'Active route. Returns the same shape as the legacy Railway /api/athlete-memory/admin/work-status — currentPriority, currentBlocker, nextAction, androidReleaseStatus, iosReleaseStatus, healthSourceStatus, adminDevStatus, feedbackSummary, backlogSummary, manualSteps, canDeleteFromNotes, doNotDeleteYet — once connector_work_status table is created and Supabase secrets set.',
          schemaRequired: CONNECTOR_SCHEMA_REQUIREMENTS.work_status,
        },
      });
    }

    // ── /handoff ───────────────────────────────────────────────────────
    if (request.method === 'GET' && path === '/handoff') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse({
        ...buildMeta(env),
        handoff: {
          status: 'repo-only',
          notes:
            'Handoff blocks (most-recent CHATGPT_STATUS) will surface here once Supabase reads land. Until then, the canonical source is Aaron paste from the Admin/Dev Prompt bridge.',
        },
      });
    }

    // ── /automation-state ──────────────────────────────────────────────
    if (request.method === 'GET' && path === '/automation-state') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse({
        ...buildMeta(env),
        automation: {
          status: 'repo-only',
          notes:
            'Will mirror admin/status booleans (workflowDispatchAvailable, releaseAuditAvailable, otaBlocked).',
        },
      });
    }

    // ── /pending-suggestions ───────────────────────────────────────────
    if (request.method === 'GET' && path === '/pending-suggestions') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse({
        ...buildMeta(env),
        pendingSuggestions: {
          status: 'repo-only',
          count: 0,
          notes:
            'Connector-driven backlog drafts will surface here when the write wave lands. See docs/CONNECTOR_BACKLOG_TOOLS_PLAN.md.',
        },
      });
    }

    // ── MCP connector routes ───────────────────────────────────────────
    // Mirror chat-app/src/server/routes/mcpRoutes.ts (commit b6fe1ad).
    // Shape source of truth: chat-app/src/server/types/connector.ts.
    // Sanitisation: docs/CONNECTOR_SANITIZATION_RULES.md.
    //
    // While Railway is suspended these four are the canonical
    // connector surface; the mobile app + ChatGPT Connector both
    // read from here.
    if (request.method === 'GET' && path === '/api/work_status') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      const fetched = await tryReadSingleRowPayload(env, 'work_status', 'connector_work_status');
      if (fetched.source === 'supabase') {
        return jsonResponse(applyConnectorRedaction({
          ...(fetched.payload as object),
          dataSource: { source: 'supabase' as const, table: 'connector_work_status' },
          generatedAt: new Date().toISOString(),
        }));
      }
      return jsonResponse(applyConnectorRedaction(placeholderWorkStatus(env)));
    }

    if (request.method === 'GET' && path === '/api/coder_lanes') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      const adapter = getSupabaseAdapter(env);
      if (adapter.configured) {
        const rows = await adapter.fetchCoderLaneRows();
        if (rows && rows.length > 0) {
          return jsonResponse(applyConnectorRedaction({
            schemaVersion: CONNECTOR_SCHEMA_VERSION,
            generatedAt: new Date().toISOString(),
            dataSource: { source: 'supabase' as const, table: 'connector_coder_lanes' },
            lanes: rows.map((r) => r.payload),
          }));
        }
      }
      return jsonResponse(applyConnectorRedaction(placeholderCoderLanes(env)));
    }

    if (request.method === 'GET' && path === '/api/build_status') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      const fetched = await tryReadSingleRowPayload(env, 'build_status', 'connector_build_status');
      if (fetched.source === 'supabase') {
        return jsonResponse(applyConnectorRedaction({
          ...(fetched.payload as object),
          dataSource: { source: 'supabase' as const, table: 'connector_build_status' },
          generatedAt: new Date().toISOString(),
        }));
      }
      return jsonResponse(applyConnectorRedaction(placeholderBuildStatus(env)));
    }

    if (request.method === 'GET' && path === '/api/handoff') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      const fetched = await tryReadSingleRowPayload(env, 'handoff', 'connector_handoff');
      if (fetched.source === 'supabase') {
        return jsonResponse(applyConnectorRedaction({
          ...(fetched.payload as object),
          dataSource: { source: 'supabase' as const, table: 'connector_handoff' },
          generatedAt: new Date().toISOString(),
        }));
      }
      return jsonResponse(applyConnectorRedaction(placeholderHandoff(env)));
    }

    if (request.method === 'GET' && path === '/api/control_centre') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      const snapshot = await buildControlCentreSnapshot(env);
      return jsonResponse(applyConnectorRedaction(snapshot));
    }

    if (request.method === 'GET' && path === '/api/terminal_summary') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      const adapter = getSupabaseAdapter(env);
      const generatedAt = new Date().toISOString();
      if (adapter.configured) {
        const entries = await adapter.fetchTerminalEntries(50);
        if (entries) {
          return jsonResponse(applyConnectorRedaction({
            schemaVersion: CONNECTOR_SCHEMA_VERSION,
            generatedAt,
            dataSource: { source: 'supabase' as const, table: 'connector_terminal_summary' },
            entries,
          }));
        }
      }
      return jsonResponse(applyConnectorRedaction({
        schemaVersion: CONNECTOR_SCHEMA_VERSION,
        generatedAt,
        dataSource: dataSourceFor(env, 'terminal_summary'),
        entries: [],
      }));
    }

    // ── Write endpoints intentionally absent ───────────────────────────
    // POST /suggestions / lane-status / terminal-summary stay unimplemented
    // until the bridge producer ships per
    // docs/CONNECTOR_SANITIZATION_RULES.md "Lane-status detection".

    return notFound();
  },
};
