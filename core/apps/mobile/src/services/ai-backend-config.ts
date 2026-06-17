/**
 * Centralized AI backend config for mobile.
 * All AI sync services and the Coach client read from here.
 *
 * Values come from Expo env vars (EXPO_PUBLIC_*).
 * Fallbacks use localhost for simulator development only.
 *
 * For physical device testing, set EXPO_PUBLIC_AI_BACKEND_URL
 * to your Mac's LAN IP (e.g. http://192.168.1.x:3000/v1/internal).
 *
 * For production, set the deployed backend URL in .env.production.
 *
 * Security: EXPO_PUBLIC_INTERNAL_API_TOKEN is a dev-only convenience.
 * Production builds with empty tokens disable all backend sync
 * (local-only mode). All sync services bail early on empty token.
 */

const DEV_INTERNAL = 'http://localhost:3000/v1/internal';
const DEV_PUBLIC = 'http://localhost:3000/api/athlete-memory';

/** Internal API base (for health/nutrition/HIIT ingest) */
export const AI_INTERNAL_BASE =
  process.env.EXPO_PUBLIC_AI_BACKEND_URL || DEV_INTERNAL;

/** Public API base (for /ai-context, /coach/ask, /health-check) */
export const AI_PUBLIC_BASE =
  process.env.EXPO_PUBLIC_AI_PUBLIC_URL || DEV_PUBLIC;

/** Internal API token for backend ingest routes */
export const AI_INTERNAL_TOKEN =
  process.env.EXPO_PUBLIC_INTERNAL_API_TOKEN ?? '';

/** Public API token for athlete-memory routes */
export const AI_PUBLIC_TOKEN =
  process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';

/**
 * Dev-only athlete ID override.
 *
 * DO NOT USE AS A PRODUCTION FALLBACK. Each authenticated user must
 * use their own Supabase user.id as the athleteId. Using a shared
 * fallback (e.g. 'dev-athlete') would leak another user's data.
 *
 * Production code: derive athleteId from useAuthStore.getState().user?.id.
 * Only fall back to this dev ID when no user is signed in AND this is
 * a dev build.
 */
export const DEV_ATHLETE_ID_OVERRIDE =
  process.env.EXPO_PUBLIC_ATHLETE_ID ?? null;

/**
 * Resolve the athleteId to use for a request.
 * Returns null if no user is signed in — callers MUST handle null.
 * Never returns a shared/default athleteId for authenticated requests.
 */
export function resolveAthleteId(userId: string | null | undefined): string | null {
  if (userId) return userId;
  // Only allow dev override when no user is signed in AND backend is local
  if (AI_BACKEND_IS_LOCAL && DEV_ATHLETE_ID_OVERRIDE) return DEV_ATHLETE_ID_OVERRIDE;
  return null;
}

/** Whether AI backend is configured (at least one token present) */
export const AI_BACKEND_CONFIGURED =
  AI_INTERNAL_TOKEN.length > 0 || AI_PUBLIC_TOKEN.length > 0;

/** Whether backend URL is localhost (simulator only, won't work on device) */
export const AI_BACKEND_IS_LOCAL =
  AI_INTERNAL_BASE.includes('localhost') || AI_INTERNAL_BASE.includes('127.0.0.1');

/**
 * Whether this is a production build with no backend URL configured.
 * In this state, all sync services are disabled and the app works
 * in local-only mode. This is safe — no network calls are made.
 */
export const AI_BACKEND_DISABLED =
  !AI_BACKEND_CONFIGURED && AI_INTERNAL_BASE === DEV_INTERNAL;

/**
 * Optional MCP / app-dev-centre Cloudflare Worker base URL.
 *
 * Production traffic continues to hit the existing Railway-hosted
 * backend at AI_PUBLIC_BASE / AI_INTERNAL_BASE until the owner flips
 * the EAS env values after live Worker verification.
 *
 * Set EXPO_PUBLIC_MCP_BASE_URL to route Admin/Dev connector status
 * reads to the Worker without flipping the core athlete-memory,
 * ingest, feedback, WHOOP, or Polar paths off Railway. The mobile
 * app does NOT auto-fallback between the two — this is a deliberate
 * switch the owner toggles once Worker verification is complete.
 *
 * See docs/CLOUDFLARE_MIGRATION.md for cutover steps.
 */
export const MCP_BASE_URL: string | null =
  (process.env.EXPO_PUBLIC_MCP_BASE_URL ?? '').trim().length > 0
    ? (process.env.EXPO_PUBLIC_MCP_BASE_URL ?? '').trim()
    : null;

/** True when the Cloudflare Worker MCP base URL is wired in env. */
export const MCP_BACKEND_CONFIGURED = MCP_BASE_URL !== null;

/**
 * Suffix paths the worker exposes that callers may have included in
 * `EXPO_PUBLIC_MCP_BASE_URL`. Order matters — longer suffixes first
 * so we strip `/mcp/v2/admin` before `/mcp/v2`. The legacy `/api`
 * suffix from the Railway era is also tolerated.
 *
 * Bug-fix history (2026-05-09): the iPhone v19 EAS env was set to
 * the full `<root>/mcp/v2` URL, and both the MCP-v2 and
 * connector-status clients re-appended `/mcp/v2` (or `/api`),
 * producing 404 paths like `/mcp/v2/mcp/v2` and `/mcp/v2/api/*`.
 * Centralising the strip-suffix logic here makes the clients
 * tolerant of either env form (worker root or full /mcp/v2 URL).
 */
const MCP_KNOWN_SUFFIX_PATHS: ReadonlyArray<string> = [
  '/mcp/v2/admin',
  '/mcp/v2/website',
  '/mcp/v2/health',
  '/mcp/v2',
  '/mcp/core',
  '/mcp/public',
  '/api',
];

/**
 * Normalise an arbitrary MCP base URL string to the worker root
 * with no trailing slash. Pure helper — the test suite calls this
 * directly with synthetic inputs, while production callers go
 * through `mcpWorkerRootUrl()` which reads the env on every call.
 */
export function normaliseMcpWorkerRootUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let trimmed = raw.replace(/\/$/, '');
  for (const suffix of MCP_KNOWN_SUFFIX_PATHS) {
    if (trimmed.toLowerCase().endsWith(suffix)) {
      trimmed = trimmed.slice(0, -suffix.length);
      break;
    }
  }
  return trimmed.replace(/\/$/, '');
}

/**
 * Normalise `EXPO_PUBLIC_MCP_BASE_URL` to the worker root with no
 * trailing slash. Tolerant of every form the env has shipped in
 * (bare hostname, `<root>/api`, `<root>/mcp/v2`,
 * `<root>/mcp/v2/admin`). Returns null when the env is unset.
 *
 * Reads `process.env` on every call so test rigs and runtime
 * config refreshes both work. Callers should use the result and
 * append exactly the path they need (`/mcp/v2`, `/mcp/v2/admin`,
 * `/api`, `/mcp/public`, etc.) — never re-derive paths in the
 * call sites.
 */
export function mcpWorkerRootUrl(): string | null {
  const raw = (process.env.EXPO_PUBLIC_MCP_BASE_URL ?? '').trim();
  return normaliseMcpWorkerRootUrl(raw.length > 0 ? raw : null);
}
