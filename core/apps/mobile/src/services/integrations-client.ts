/**
 * Mobile client for per-user integration routes (Polar, Cronometer,
 * WHOOP direct, Concept2). Hits /api/integrations/...
 */
import { AI_PUBLIC_BASE, AI_PUBLIC_TOKEN, resolveAthleteId } from './ai-backend-config';

const TIMEOUT_MS = 12_000;

function buildOrigin(): string {
  try { return new URL(AI_PUBLIC_BASE).origin; } catch { return 'http://localhost:3000'; }
}

export interface IntegrationClientConfig {
  baseUrl: string;
  token: string;
  athleteId: string;
  supabaseAccessToken: string | null;
}

export function buildIntegrationConfig(
  userId: string | null | undefined,
  accessToken: string | null | undefined,
): IntegrationClientConfig | null {
  const athleteId = resolveAthleteId(userId);
  if (!athleteId) return null;
  return { baseUrl: buildOrigin(), token: AI_PUBLIC_TOKEN, athleteId, supabaseAccessToken: accessToken ?? null };
}

function headers(cfg: IntegrationClientConfig): Record<string, string> {
  const h: Record<string, string> = {
    'Content-Type': 'application/json',
    'x-athlete-memory-token': cfg.token,
    'x-athlete-id': cfg.athleteId,
  };
  if (cfg.supabaseAccessToken) h['Authorization'] = `Bearer ${cfg.supabaseAccessToken}`;
  return h;
}

async function req<T>(method: 'GET' | 'POST', url: string, cfg: IntegrationClientConfig, body?: unknown, timeoutMs?: number): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), timeoutMs ?? TIMEOUT_MS);
  try {
    const r = await fetch(url, { method, signal: c.signal, headers: headers(cfg), body: body ? JSON.stringify(body) : undefined });
    clearTimeout(t);
    if (!r.ok) return { ok: false, error: (await r.text().catch(() => '')).slice(0, 300) || `HTTP ${r.status}` };
    return { ok: true, data: (await r.json()) as T };
  } catch (e) { clearTimeout(t); return { ok: false, error: e instanceof Error ? e.message : 'Network error' }; }
}

// Polar
export const getPolarStatus = (cfg: IntegrationClientConfig) => req<any>('GET', `${cfg.baseUrl}/api/integrations/polar/status`, cfg);
export const getPolarConnectUrl = (cfg: IntegrationClientConfig) => req<{ url: string; state: string }>('GET', `${cfg.baseUrl}/api/integrations/polar/connect`, cfg);
export const disconnectPolar = (cfg: IntegrationClientConfig) => req<any>('POST', `${cfg.baseUrl}/api/integrations/polar/disconnect`, cfg);
export const syncPolar = (cfg: IntegrationClientConfig) => req<any>('POST', `${cfg.baseUrl}/api/integrations/polar/sync`, cfg);

// Cronometer
export const getCronometerStatus = (cfg: IntegrationClientConfig) => req<any>('GET', `${cfg.baseUrl}/api/integrations/cronometer/status`, cfg);

// WHOOP direct
export const getWhoopStatus = (cfg: IntegrationClientConfig) => req<any>('GET', `${cfg.baseUrl}/api/integrations/whoop/status`, cfg);
export const getWhoopConnectUrl = (cfg: IntegrationClientConfig) => req<{ url: string; state: string }>('GET', `${cfg.baseUrl}/api/integrations/whoop/connect`, cfg);
export const disconnectWhoop = (cfg: IntegrationClientConfig) => req<any>('POST', `${cfg.baseUrl}/api/integrations/whoop/disconnect`, cfg);
export const syncWhoop = (cfg: IntegrationClientConfig) => req<any>('POST', `${cfg.baseUrl}/api/integrations/whoop/sync`, cfg);
/**
 * Deep WHOOP backfill. The backend reads `{ deep: true, daysBack }`
 * from the body; servers that don't yet understand it just run a
 * normal sync (the `deep` flag is ignored), so this is safe to ship
 * independently of backend changes.
 */
export const backfillWhoop = (cfg: IntegrationClientConfig, daysBack = 365) =>
  req<any>('POST', `${cfg.baseUrl}/api/integrations/whoop/sync`, cfg, { deep: true, daysBack });

// WHOOP CSV (optional manual enrichment — deep history)
export const getWhoopCsvStatus = (cfg: IntegrationClientConfig) =>
  req<any>('GET', `${cfg.baseUrl}/api/integrations/whoop/csv/status`, cfg);
export const uploadWhoopCsv = (cfg: IntegrationClientConfig, files: Record<string, string>) =>
  req<any>('POST', `${cfg.baseUrl}/api/integrations/whoop/csv/upload`, cfg, { files });
/**
 * One-shot zip upload — mobile picks the WHOOP export .zip,
 * encodes to base64, and sends. Backend unzips + auto-detects.
 */
export const uploadWhoopZip = (cfg: IntegrationClientConfig, zipBase64: string) =>
  // 3-min ceiling — WHOOP exports can legitimately take 30-60s to
  // transfer + extract on a slow connection. The default 12s would
  // abort mid-upload and surface as a "crash" because the JS side
  // never sees a graceful error.
  req<any>('POST', `${cfg.baseUrl}/api/integrations/whoop/csv/upload-zip`, cfg, { zipBase64 }, 180_000);
export const clearWhoopCsv = (cfg: IntegrationClientConfig) =>
  req<any>('POST', `${cfg.baseUrl}/api/integrations/whoop/csv/clear`, cfg);

// Concept2
export const getConcept2Status = (cfg: IntegrationClientConfig) => req<any>('GET', `${cfg.baseUrl}/api/integrations/concept2/status`, cfg);

// Samsung Health
export const getSamsungHealthStatus = (cfg: IntegrationClientConfig) => req<any>('GET', `${cfg.baseUrl}/api/integrations/samsung-health/status`, cfg);
