/**
 * Shared `Env` type for the Cloudflare Worker.
 *
 * Lives in its own file so the Supabase adapter (and any future
 * sibling modules) can import it without pulling in the whole
 * worker.ts request handler.
 */

export interface Env {
  WORKER_MODE?: string;
  /**
   * Deprecated. Railway is no longer the active backend; this URL
   * is retained as a legacy reference only and the Worker never
   * proxies requests through it. See docs/CLOUDFLARE_MIGRATION.md
   * § "Railway deprecated".
   */
  RAILWAY_FALLBACK_URL?: string;
  ATHLETE_MEMORY_API_TOKEN?: string;
  SUPABASE_URL?: string;
  SUPABASE_SERVICE_ROLE_KEY?: string;
}
