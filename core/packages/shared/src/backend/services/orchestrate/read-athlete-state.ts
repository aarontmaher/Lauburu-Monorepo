/**
 * Read orchestrator — enforces cached-artifact-first read order.
 *
 * This is the SINGLE entry point for athlete state reads. All
 * callers (chat, API, jobs) go through this. No caller may
 * bypass this to hit normalized, raw, or live WHOOP directly.
 *
 * Read order (strictly enforced):
 *   1. latest daily_refresh_artifact
 *   2. latest weekly_synthesis_artifact
 *   3. stable private athlete memory
 *   4. normalized_daily_metrics (only if artifact lacks required fields)
 *   5. raw source records (only if normalized lacks required fields)
 *   6. live WHOOP (only if freshness policy explicitly allows)
 *
 * The orchestrator returns a typed result indicating which layers
 * were consulted and why, so callers and the AI can reason about
 * data provenance and freshness without guessing.
 */

import type { DailyRefreshArtifact, WeeklySynthesisArtifact, ArtifactConfidence } from '../../contracts/refresh-artifacts.types';
import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';
import type { WhoopDailyMetricsRaw } from '../../contracts/whoop-raw.types';
import type { FreshnessDecisionResult, SourceHealthStatus } from '../../contracts/freshness.types';
import type { AthleteMemoryRecord } from '../../../athlete-memory/types';
import { shouldReadLiveWhoop } from '../freshness/should-read-live-whoop';

// ---------------------------------------------------------------------------
// Storage adapter interface — callers inject their persistence layer
// ---------------------------------------------------------------------------

/**
 * Backend storage reads. Implementors provide file-backed, Supabase,
 * or in-memory versions. The orchestrator does not know or care
 * which storage backend is used.
 */
export interface AthleteStateStore {
  getLatestDailyRefresh(athleteId: string): Promise<DailyRefreshArtifact | null>;
  getLatestWeeklySynthesis(athleteId: string): Promise<WeeklySynthesisArtifact | null>;
  getStableMemory(athleteId: string): Promise<AthleteMemoryRecord | null>;
  getNormalizedDay(athleteId: string, date: string): Promise<NormalizedDailyMetrics | null>;
  getNormalizedRecent(athleteId: string, days: number): Promise<NormalizedDailyMetrics[]>;
  getRawDay(athleteId: string, date: string): Promise<WhoopDailyMetricsRaw | null>;
  getSourceHealth(athleteId: string, provider: string): Promise<SourceHealthStatus | null>;
}

/**
 * Live WHOOP read adapter. Only called when freshness policy
 * explicitly allows it. Returns normalized metrics (the live
 * read result is immediately normalized, never served raw).
 */
export interface LiveWhoopReader {
  fetchAndNormalize(athleteId: string, date: string): Promise<NormalizedDailyMetrics | null>;
}

// ---------------------------------------------------------------------------
// Read request / result types
// ---------------------------------------------------------------------------

export interface ReadAthleteStateRequest {
  athleteId: string;
  /** The date the caller needs state for (default: today). */
  date?: string;
  /** Whether the user explicitly requested real-time data. */
  userRequestedRealtime?: boolean;
  /** Fields the caller requires — triggers deeper fallback if missing. */
  requiredFields?: string[];
}

/** Which layer provided the data and why. */
export type ResolvedLayer =
  | 'daily_artifact'
  | 'weekly_artifact'
  | 'stable_memory'
  | 'normalized'
  | 'raw'
  | 'live_whoop';

export interface LayerConsulted {
  layer: ResolvedLayer;
  reason: string;
  hit: boolean;
}

export interface ReadAthleteStateResult {
  athleteId: string;
  date: string;

  /** The primary artifact used for reasoning (if available). */
  dailyArtifact: DailyRefreshArtifact | null;
  weeklyArtifact: WeeklySynthesisArtifact | null;
  stableMemory: AthleteMemoryRecord | null;

  /** Supplemental normalized data (only fetched if artifact was insufficient). */
  normalizedDay: NormalizedDailyMetrics | null;

  /** Which layers were consulted and why. */
  layersConsulted: LayerConsulted[];

  /** Whether a live WHOOP read was performed. */
  liveWhoopRead: boolean;
  freshnessDecision: FreshnessDecisionResult | null;

  /** Overall confidence of the resolved state. */
  confidence: ArtifactConfidence;

  /** Fields still missing after all fallback layers. */
  stillMissing: string[];
}

// ---------------------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------------------

function todayDate(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Read athlete state through the enforced cache-first order.
 *
 * This function is the ONLY way backend callers should read
 * athlete state. It guarantees the read order is respected
 * and returns full provenance of which layers were used.
 */
export async function readAthleteState(
  request: ReadAthleteStateRequest,
  store: AthleteStateStore,
  liveReader?: LiveWhoopReader,
): Promise<ReadAthleteStateResult> {
  const { athleteId, requiredFields = [], userRequestedRealtime = false } = request;
  const date = request.date ?? todayDate();
  const layers: LayerConsulted[] = [];
  let stillMissing = [...requiredFields];

  function markResolved(fields: string[]) {
    stillMissing = stillMissing.filter((f) => !fields.includes(f));
  }

  // ── Step 1: Daily artifact ──────────────────────────────────
  const dailyArtifact = await store.getLatestDailyRefresh(athleteId);
  const dailyUsable = dailyArtifact != null && dailyArtifact.sourceDate === date;
  layers.push({
    layer: 'daily_artifact',
    reason: dailyUsable
      ? 'Fresh daily artifact for target date'
      : dailyArtifact
        ? `Daily artifact exists but for ${dailyArtifact.sourceDate}, not ${date}`
        : 'No daily artifact',
    hit: dailyUsable,
  });
  if (dailyUsable) {
    // The daily artifact's coverage tells us what's present
    const artifactFields = dailyArtifact.facts
      .filter((f) => f.status !== 'missing')
      .map((f) => f.metric);
    markResolved(artifactFields);
  }

  // ── Step 2: Weekly artifact ─────────────────────────────────
  const weeklyArtifact = await store.getLatestWeeklySynthesis(athleteId);
  const weeklyUsable = weeklyArtifact != null;
  layers.push({
    layer: 'weekly_artifact',
    reason: weeklyUsable
      ? `Weekly artifact for ${weeklyArtifact.weekStart}–${weeklyArtifact.weekEnd}`
      : 'No weekly artifact',
    hit: weeklyUsable,
  });

  // ── Step 3: Stable memory ───────────────────────────────────
  const stableMemory = await store.getStableMemory(athleteId);
  layers.push({
    layer: 'stable_memory',
    reason: stableMemory ? `Updated ${stableMemory.updatedAt}` : 'No stable memory',
    hit: stableMemory != null,
  });

  // ── Step 4: Normalized (only if artifact insufficient) ──────
  let normalizedDay: NormalizedDailyMetrics | null = null;
  if (stillMissing.length > 0 || !dailyUsable) {
    normalizedDay = await store.getNormalizedDay(athleteId, date);
    const normHit = normalizedDay != null;
    layers.push({
      layer: 'normalized',
      reason: normHit
        ? `Normalized record for ${date}`
        : `No normalized record for ${date}`,
      hit: normHit,
    });
    if (normHit) {
      markResolved(normalizedDay!.presentFields);
    }
  }

  // ── Step 5: Raw (only if normalized insufficient) ───────────
  if (stillMissing.length > 0) {
    const rawDay = await store.getRawDay(athleteId, date);
    layers.push({
      layer: 'raw',
      reason: rawDay
        ? `Raw record for ${date}`
        : `No raw record for ${date}`,
      hit: rawDay != null,
    });
    // Raw doesn't directly resolve required fields (it's not
    // normalized), but its existence informs freshness decisions.
  }

  // ── Step 6: Live WHOOP (only if freshness policy allows) ────
  let liveWhoopRead = false;
  let freshnessDecision: FreshnessDecisionResult | null = null;

  if (stillMissing.length > 0 || !dailyUsable || userRequestedRealtime) {
    const sourceHealth = await store.getSourceHealth(athleteId, 'whoop');
    freshnessDecision = shouldReadLiveWhoop({
      latestArtifactFreshUntil: dailyArtifact?.freshUntil ?? null,
      sourceHealth,
      userRequestedRealtime,
      requiredFields,
      cachedPresentFields: normalizedDay?.presentFields ?? [],
    });

    if (freshnessDecision.liveReadAllowed && liveReader) {
      const liveResult = await liveReader.fetchAndNormalize(athleteId, date);
      liveWhoopRead = true;
      layers.push({
        layer: 'live_whoop',
        reason: `Live read: ${freshnessDecision.reason}`,
        hit: liveResult != null,
      });
      if (liveResult) {
        normalizedDay = liveResult;
        markResolved(liveResult.presentFields);
      }
    } else {
      layers.push({
        layer: 'live_whoop',
        reason: freshnessDecision.liveReadAllowed
          ? 'Live read allowed but no reader provided'
          : `Denied: ${freshnessDecision.reason}`,
        hit: false,
      });
    }
  }

  // ── Resolve confidence ──────────────────────────────────────
  let confidence: ArtifactConfidence = 'low';
  if (dailyUsable && dailyArtifact!.confidence === 'high') {
    confidence = 'high';
  } else if (dailyUsable) {
    confidence = dailyArtifact!.confidence;
  } else if (normalizedDay && normalizedDay.completeness === 'complete') {
    confidence = 'medium';
  }

  return {
    athleteId,
    date,
    dailyArtifact: dailyUsable ? dailyArtifact : null,
    weeklyArtifact,
    stableMemory,
    normalizedDay,
    layersConsulted: layers,
    liveWhoopRead,
    freshnessDecision,
    confidence,
    stillMissing,
  };
}
