/**
 * Lauburu MCP / app-dev-centre Cloudflare Worker — scaffold.
 *
 * Status today: REPO-ONLY. Aaron has not deployed this Worker
 * yet; production traffic continues hitting the Railway-hosted
 * `chat-app/src/server` Express app at
 * `https://lauburu-ai-backend-production.up.railway.app`.
 *
 * Purpose: have a Cloudflare-Workers-shaped surface ready to take
 * over the public MCP / app-dev-centre layer when Railway billing
 * becomes a blocker. Supabase remains the database / auth / state
 * layer regardless of where this control surface lives.
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

export interface Env {
  WORKER_MODE?: string;
  RAILWAY_FALLBACK_URL?: string;
  ATHLETE_MEMORY_API_TOKEN?: string;
  SUPABASE_URL?: string;
  SUPABASE_SERVICE_ROLE_KEY?: string;
}

interface ConnectorMeta {
  generatedAt: string;
  provider: 'cloudflare-workers';
  mode: string;
  workerName: string;
  supabaseConfigured: boolean;
  railwayRequired: false;
  railwayFallbackUrl: string | null;
}

function buildMeta(env: Env): ConnectorMeta {
  return {
    generatedAt: new Date().toISOString(),
    provider: 'cloudflare-workers',
    mode: env.WORKER_MODE ?? 'unknown',
    workerName: 'lauburu-mcp',
    supabaseConfigured: !!env.SUPABASE_URL && !!env.SUPABASE_SERVICE_ROLE_KEY,
    railwayRequired: false,
    railwayFallbackUrl: env.RAILWAY_FALLBACK_URL ?? null,
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

function buildWorkStatus(env: Env) {
  const generatedAt = new Date().toISOString();
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt,
    currentPriority:
      'Cloudflare Worker is the live MCP connector surface; secret installed; routes admin-token gated.',
    currentBlocker:
      'Tmux bridge producer not operational; coder_lanes / build_status / handoff payloads are provisional placeholders.',
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
      lastCommitMessage: 'unknown until local bridge populates this field',
    },
    nextAction:
      'Stand up the tmux bridge producer to replace the placeholder coder_lanes / handoff payloads with live data.',
  };
}

function buildCoderLanes() {
  const generatedAt = new Date().toISOString();
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt,
    lanes: [
      {
        laneId: 'claude' as const,
        status: 'idle' as const,
        lastSeenAt: generatedAt,
        currentPromptId: null,
        lastPromptId: 'CLAUDE-CLOUDFLARE-CUTOVER-MCP-ROUTES-01',
        lastSummary:
          'Claude lane parked after Cloudflare cutover deploy. Awaiting next owner-reviewed handoff.',
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

function buildBuildStatus() {
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
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

function buildHandoff() {
  return {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
    latestClaudePrompt: 'CLAUDE-CLOUDFLARE-CUTOVER-MCP-ROUTES-01',
    latestCodexPrompt: 'CODEX-BACKEND-API-AI-IMPLEMENTATION-01',
    manualSteps: [
      'Aaron: decide whether to resolve Railway suspension or stay on Cloudflare permanently.',
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
          'GET /mcp/health',
          'GET /app-dev-centre/status',
          'GET /handoff',
          'GET /automation-state',
          'GET /pending-suggestions',
          'GET /api/work_status',
          'GET /api/coder_lanes',
          'GET /api/build_status',
          'GET /api/handoff',
        ],
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
          status: 'repo-only',
          notes:
            'Worker scaffold is reachable but does not yet read Supabase or proxy Railway. Stage 2 is wiring Supabase reads via SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.',
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
          status: 'repo-only',
          notes:
            'When wired, this returns the same shape as Railway /api/athlete-memory/admin/work-status — currentPriority, currentBlocker, nextAction, androidReleaseStatus, iosReleaseStatus, healthSourceStatus, adminDevStatus, feedbackSummary, backlogSummary, manualSteps, canDeleteFromNotes, doNotDeleteYet.',
          fallback: env.RAILWAY_FALLBACK_URL
            ? `${env.RAILWAY_FALLBACK_URL}/api/athlete-memory/admin/work-status`
            : null,
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
      return jsonResponse(applyConnectorRedaction(buildWorkStatus(env)));
    }

    if (request.method === 'GET' && path === '/api/coder_lanes') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse(applyConnectorRedaction(buildCoderLanes()));
    }

    if (request.method === 'GET' && path === '/api/build_status') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse(applyConnectorRedaction(buildBuildStatus()));
    }

    if (request.method === 'GET' && path === '/api/handoff') {
      const auth = requireAdminToken(request, env);
      if (!auth.ok) return jsonResponse({ ok: false, error: auth.reason }, { status: 403 });
      return jsonResponse(applyConnectorRedaction(buildHandoff()));
    }

    // ── Write endpoints intentionally absent ───────────────────────────
    // POST /suggestions / lane-status / terminal-summary stay unimplemented
    // until the bridge producer ships per
    // docs/CONNECTOR_SANITIZATION_RULES.md "Lane-status detection".

    return notFound();
  },
};
