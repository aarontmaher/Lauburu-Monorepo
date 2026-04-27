/**
 * Athlete health-check — one canonical backend summary that tells the
 * mobile app whether this athlete is in seed mode or live mode, what
 * sources are available, what artifacts are fresh, and what the API AI
 * is safe to do right now.
 *
 * Pure function — reads from existing backend state, derives everything.
 * Does NOT write anything. Does NOT call live WHOOP.
 */

import type { DailyRefreshArtifact, WeeklySynthesisArtifact, ArtifactConfidence } from '../../contracts/refresh-artifacts.types';
import type { SourceHealthStatus, FreshnessStatus } from '../../contracts/freshness.types';
import type { AthleteMemoryRecord } from '../../../athlete-memory/types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AthleteMode =
  | 'seed_partial'     // running from cached seed, no live WHOOP
  | 'live_partial'     // live WHOOP connected but some domains missing
  | 'live_ready'       // live WHOOP fully covering required domains
  | 'uninitialized';   // no stable memory or artifacts exist

export interface DomainCoverage {
  domain: string;
  lastDate: string | null;
  status: FreshnessStatus | 'not_configured';
}

export interface ArtifactFreshnessSummary {
  type: 'daily' | 'weekly';
  available: boolean;
  sourceDate: string | null;
  isFreshForToday: boolean;
  confidence: ArtifactConfidence | null;
}

export interface AthleteHealthCheck {
  athleteId: string;
  checkedAt: string;

  /** Overall mode — the single most important field for consumers. */
  mode: AthleteMode;

  /** Seed-mode flags (consistent with SeedModeMetadata). */
  seedMode: boolean;
  provisionalUntilDirectWhoop: boolean;

  /** Source health summary. */
  sourceHealth: {
    whoop: {
      connected: boolean;
      freshnessStatus: FreshnessStatus | 'not_configured';
      upstreamStatus: string;
      lastIngestAt: string | null;
      degradedReason: string | null;
    };
    coverageByDomain: DomainCoverage[];
  };

  /** Artifact freshness summary. */
  artifacts: {
    daily: ArtifactFreshnessSummary;
    weekly: ArtifactFreshnessSummary;
    stableMemoryPresent: boolean;
    stableMemoryUpdatedAt: string | null;
  };

  /** WHOOP-native fields that are currently missing or stale. */
  missingWhoopNativeFields: string[];

  /** What the API AI can safely do in the current state. */
  safeFor: string[];
  /** What the API AI should NOT do in the current state. */
  notSafeFor: string[];

  /** Recommended read path order for the current state. */
  recommendedReadOrder: string[];

  /** Recent seed→live transition attempt, if any. */
  lastTransitionAttempt: {
    attempted: boolean;
    succeededAt: string | null;
    failedAt: string | null;
    failedReason: string | null;
  };
}

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

export interface DeriveHealthCheckInput {
  athleteId: string;
  today: string;
  dailyArtifact: DailyRefreshArtifact | null;
  weeklyArtifact: WeeklySynthesisArtifact | null;
  stableMemory: AthleteMemoryRecord | null;
  whoopHealth: SourceHealthStatus | null;
}

// ---------------------------------------------------------------------------
// Derivation
// ---------------------------------------------------------------------------

export function deriveHealthCheck(input: DeriveHealthCheckInput): AthleteHealthCheck {
  const { athleteId, today, dailyArtifact, weeklyArtifact, stableMemory, whoopHealth } = input;
  const now = new Date().toISOString();

  // Mode derivation
  const hasMemory = stableMemory != null;
  const whoopFresh = whoopHealth?.freshnessStatus === 'fresh';
  const whoopConnected = whoopHealth != null && whoopHealth.upstreamStatus !== 'unknown';
  const dailyFreshToday = dailyArtifact?.sourceDate === today;
  const hasSeedMarker = (dailyArtifact as any)?.seedMode === true;

  let mode: AthleteMode;
  if (!hasMemory) {
    mode = 'uninitialized';
  } else if (whoopFresh && dailyFreshToday && !hasSeedMarker) {
    mode = 'live_ready';
  } else if (whoopConnected && !whoopFresh) {
    mode = 'live_partial';
  } else {
    mode = 'seed_partial';
  }

  const seedMode = mode === 'seed_partial' || mode === 'uninitialized';
  const provisionalUntilDirectWhoop = !whoopFresh;

  // Source health
  const coverageByDomain: DomainCoverage[] = [];
  const missingFields: string[] = [];
  const domainMap = whoopHealth?.coverageByDomain ?? {};
  for (const [domain, info] of Object.entries(domainMap)) {
    const domInfo = info as { lastDate: string | null; status: string };
    coverageByDomain.push({
      domain,
      lastDate: domInfo.lastDate,
      status: (domInfo.status as FreshnessStatus) ?? 'missing',
    });
    if (domInfo.status === 'missing' || domInfo.status === 'stale') {
      missingFields.push(domain);
    }
  }
  // Standard WHOOP domains we expect
  for (const expected of ['recovery', 'sleep', 'strain', 'workouts']) {
    if (!coverageByDomain.some((d) => d.domain === expected)) {
      coverageByDomain.push({ domain: expected, lastDate: null, status: 'not_configured' });
      missingFields.push(expected);
    }
  }

  // Artifact freshness
  const dailySummary: ArtifactFreshnessSummary = {
    type: 'daily',
    available: dailyArtifact != null,
    sourceDate: dailyArtifact?.sourceDate ?? null,
    isFreshForToday: dailyFreshToday,
    confidence: dailyArtifact?.confidence ?? null,
  };
  const weeklySummary: ArtifactFreshnessSummary = {
    type: 'weekly',
    available: weeklyArtifact != null,
    sourceDate: weeklyArtifact?.weekEnd ?? null,
    isFreshForToday: weeklyArtifact != null, // weekly is valid for the whole week
    confidence: weeklyArtifact?.confidence ?? null,
  };

  // Safe/not-safe derivation
  const safeFor: string[] = [];
  const notSafeFor: string[] = [];

  if (hasMemory) safeFor.push('read_stable_memory');
  if (weeklyArtifact) safeFor.push('read_weekly_trends');
  if (dailyArtifact) safeFor.push('read_daily_artifact');
  if (dailyFreshToday) safeFor.push('display_todays_readiness');
  if (mode === 'live_ready') safeFor.push('full_coaching_recommendations');

  if (!hasMemory) notSafeFor.push('any_coaching_behavior');
  if (!dailyFreshToday) notSafeFor.push('display_todays_readiness_as_current');
  if (seedMode) notSafeFor.push('claim_live_whoop_backed_analysis');
  if (missingFields.includes('recovery')) notSafeFor.push('display_recovery_score_as_live');
  if (missingFields.includes('strain')) notSafeFor.push('display_strain_as_live');

  // Recommended read order
  const recommendedReadOrder = [
    dailyFreshToday ? 'daily_refresh_artifact (fresh)' : dailyArtifact ? 'daily_refresh_artifact (stale)' : null,
    weeklyArtifact ? 'weekly_synthesis_artifact' : null,
    hasMemory ? 'stable_athlete_memory' : null,
    'normalized_daily_metrics',
    'raw_source_records',
    provisionalUntilDirectWhoop ? null : 'live_whoop (if freshness allows)',
  ].filter(Boolean) as string[];

  // Transition state
  const lastTransitionAttempt = {
    attempted: whoopHealth?.lastFailedIngestAt != null || (whoopFresh && !hasSeedMarker),
    succeededAt: whoopFresh && !hasSeedMarker ? whoopHealth?.lastSuccessfulIngestAt ?? null : null,
    failedAt: whoopHealth?.lastFailedIngestAt ?? null,
    failedReason: whoopHealth?.degradedReason ?? null,
  };

  return {
    athleteId,
    checkedAt: now,
    mode,
    seedMode,
    provisionalUntilDirectWhoop,
    sourceHealth: {
      whoop: {
        connected: whoopConnected,
        freshnessStatus: whoopHealth?.freshnessStatus ?? 'not_configured',
        upstreamStatus: whoopHealth?.upstreamStatus ?? 'unknown',
        lastIngestAt: whoopHealth?.lastSuccessfulIngestAt ?? null,
        degradedReason: whoopHealth?.degradedReason ?? null,
      },
      coverageByDomain,
    },
    artifacts: {
      daily: dailySummary,
      weekly: weeklySummary,
      stableMemoryPresent: hasMemory,
      stableMemoryUpdatedAt: stableMemory?.updatedAt ?? null,
    },
    missingWhoopNativeFields: missingFields,
    safeFor,
    notSafeFor,
    recommendedReadOrder,
    lastTransitionAttempt,
  };
}
