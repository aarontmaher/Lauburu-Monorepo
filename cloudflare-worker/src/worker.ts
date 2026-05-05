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

    // ── Write endpoints intentionally absent ───────────────────────────
    // POST /suggestions stays unimplemented until an authenticated
    // write path exists per docs/CONNECTOR_BACKLOG_TOOLS_PLAN.md
    // second-wave spec.

    return notFound();
  },
};
