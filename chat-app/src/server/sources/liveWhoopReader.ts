/**
 * LiveWhoopReader — fetches fresh WHOOP data via MCP and normalizes it.
 *
 * Only called by the read orchestrator when freshness policy
 * explicitly allows a live read. Never the default path.
 *
 * Flow:
 *   1. Trigger MCP sync (fire-and-forget, don't wait for completion)
 *   2. Fetch today's data from bridge /data/today
 *   3. If payload matches requested date, ingest + normalize
 *   4. Save to store
 *
 * The MCP sync trigger ensures the SQLite database has current-day
 * data before we read. This replaces reliance on GitHub Actions cron.
 */

import type { LiveWhoopReader } from '../../../../packages/shared/src/backend/services/orchestrate/read-athlete-state';
import type { NormalizedDailyMetrics } from '../../../../packages/shared/src/backend/contracts/normalized-daily.types';
import { ingestWhoopDay, type WhoopMcpDayPayload } from '../../../../packages/shared/src/backend/services/whoop/ingest-whoop';
import { normalizeWhoopDay } from '../../../../packages/shared/src/backend/services/normalize/normalize-daily-metrics';
import { FileApiAiStateStore } from '../athlete-memory/file-api-ai-state-store';

const WHOOP_BRIDGE_BASE = process.env.WHOOP_BRIDGE_URL
  ?? 'https://rejalrfmievikabgsakf.supabase.co/functions/v1/whoop-bridge';
const WHOOP_MCP_DIRECT = process.env.WHOOP_MCP_URL
  ?? 'https://whoop-mcp-production-032e.up.railway.app';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY
  ?? 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJlamFscmZtaWV2aWthYmdzYWtmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzNTQ1NjYsImV4cCI6MjA4OTkzMDU2Nn0.dfE3EfP7PYTe4Pi07c65BxI1W-0NfE6vqZBFJJpL-fM';
const FETCH_TIMEOUT_MS = 10_000;
const SYNC_TRIGGER_TIMEOUT_MS = 5_000; // Don't wait long for sync trigger

/**
 * Trigger a WHOOP MCP sync. Fire-and-forget — we don't wait for
 * completion because syncs take 2-3 minutes. The data may not be
 * available immediately, but the next read will pick it up.
 */
async function triggerMcpSync(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), SYNC_TRIGGER_TIMEOUT_MS);
    // Try direct MCP first (faster, no bridge hop)
    const resp = await fetch(`${WHOOP_MCP_DIRECT}/diag/trigger-sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    });
    clearTimeout(timer);
    return resp.ok;
  } catch {
    // Direct failed — try via bridge
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), SYNC_TRIGGER_TIMEOUT_MS);
      const resp = await fetch(
        `${WHOOP_BRIDGE_BASE}?path=${encodeURIComponent('/diag/trigger-sync')}`,
        {
          method: 'POST',
          headers: {
            apikey: SUPABASE_ANON_KEY,
            Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
        },
      );
      clearTimeout(timer);
      return resp.ok;
    } catch {
      return false;
    }
  }
}

/** Track last sync trigger to avoid hammering. */
let lastSyncTriggerAt = 0;
const SYNC_TRIGGER_COOLDOWN_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Trigger sync if cooldown has elapsed. Fire-and-forget.
 */
function triggerSyncIfCooledDown(): void {
  const now = Date.now();
  if (now - lastSyncTriggerAt < SYNC_TRIGGER_COOLDOWN_MS) return;
  lastSyncTriggerAt = now;
  void triggerMcpSync().catch(() => {});
}

async function fetchWhoopToday(): Promise<WhoopMcpDayPayload | null> {
  const url = `${WHOOP_BRIDGE_BASE}?path=${encodeURIComponent('/data/today')}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const resp = await fetch(url, {
      signal: controller.signal,
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        Accept: 'application/json',
      },
    });
    if (!resp.ok) return null;
    const body = await resp.json();
    // Unwrap — the bridge may return nested shapes
    const day = body?.latest_day ?? body?.data ?? body?.today ?? body;
    if (!day || !day.local_date) return null;
    return day as WhoopMcpDayPayload;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch recent WHOOP daily summaries (multi-day).
 * Uses the bridge with /data/daily-summary?days=N path.
 */
export async function fetchWhoopRecent(days: number = 7): Promise<WhoopMcpDayPayload[]> {
  const bridgePath = `/data/daily-summary?days=${days}`;
  const url = `${WHOOP_BRIDGE_BASE}?path=${encodeURIComponent(bridgePath)}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS * 2);
  try {
    const resp = await fetch(url, {
      signal: controller.signal,
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        Accept: 'application/json',
      },
    });
    if (!resp.ok) return [];
    const body = await resp.json();
    const data = body?.data ?? body?.days ?? body;
    if (!Array.isArray(data)) {
      const today = await fetchWhoopToday();
      return today ? [today] : [];
    }
    return data.filter((d: any) => d?.local_date) as WhoopMcpDayPayload[];
  } catch {
    return [];
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Allow-list of athleteIds that own the WHOOP MCP connection.
 * ONLY these athletes can receive live WHOOP data from the bridge.
 * All other athletes see no_data/not_connected — never another user's WHOOP.
 *
 * The WHOOP bridge is a single-user proxy to Aaron's WHOOP account.
 * It must never serve that data to other users' athleteIds.
 */
const WHOOP_BRIDGE_OWNER_ATHLETE_IDS = new Set(
  (process.env.WHOOP_BRIDGE_OWNER_ATHLETE_IDS ?? 'dev-athlete')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean),
);

export function createLiveWhoopReader(store: FileApiAiStateStore): LiveWhoopReader {
  return {
    async fetchAndNormalize(athleteId: string, date: string): Promise<NormalizedDailyMetrics | null> {
      // CRITICAL: Only fetch WHOOP bridge data for the athlete who owns the WHOOP connection.
      // Never return Aaron's WHOOP data for another user's athleteId.
      if (!WHOOP_BRIDGE_OWNER_ATHLETE_IDS.has(athleteId)) {
        return null;
      }
      // Trigger a MCP sync (fire-and-forget, 5-min cooldown)
      triggerSyncIfCooledDown();

      const payload = await fetchWhoopToday();
      if (!payload) return null;
      // Only use if the payload matches the requested date
      if (payload.local_date !== date) return null;

      const raw = ingestWhoopDay(payload, athleteId);
      await store.saveRawDay(athleteId, raw);

      const normalized = normalizeWhoopDay(raw);
      await store.saveNormalizedDay(athleteId, normalized);

      // Update WHOOP source-health record
      const now = new Date().toISOString();
      const domains: Record<string, { lastDate: string | null; status: 'fresh' | 'stale' | 'expired' | 'missing' }> = {};
      if (normalized.recoveryScore != null) domains.recovery = { lastDate: date, status: 'fresh' };
      if (normalized.totalSleepHours != null) domains.sleep = { lastDate: date, status: 'fresh' };
      if (normalized.dailyStrain != null) domains.strain = { lastDate: date, status: 'fresh' };
      if (normalized.hrvMs != null) domains.hrv = { lastDate: date, status: 'fresh' };
      if (normalized.restingHrBpm != null) domains.resting_hr = { lastDate: date, status: 'fresh' };
      if (normalized.workoutCount > 0) domains.workouts = { lastDate: date, status: 'fresh' };

      await store.saveSourceHealth(athleteId, 'whoop', {
        id: `source_health_whoop_${athleteId}`,
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        athleteId,
        provider: 'whoop',
        lastSuccessfulIngestAt: now,
        lastFailedIngestAt: null,
        freshnessStatus: Object.keys(domains).length > 0 ? 'fresh' : 'missing',
        coverageByDomain: domains,
        upstreamStatus: 'healthy',
        degradedReason: null,
      } as any);

      return normalized;
    },
  };
}
