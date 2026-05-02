/**
 * AI context response — the single unified shape the API AI layer
 * consumes for athlete reasoning.
 *
 * Includes every layer the AI needs:
 *   - source health (operational truth)
 *   - latest normalized metrics (deterministic, interpretation-free)
 *   - daily refresh artifact (interpreted, athlete-relative)
 *   - weekly synthesis artifact (interpreted, weekly rollup)
 *   - baseline profile + thresholds (slow-moving stable memory)
 *   - capability summary (seed/live mode, safe_for/not_safe_for)
 *
 * The AI MUST check `capability.notSafeFor` before generating
 * readiness, recovery, or strain claims. Missing WHOOP-native
 * fields are explicitly listed — never invent them.
 */

import type { DailyRefreshArtifact, WeeklySynthesisArtifact, ArtifactConfidence } from './refresh-artifacts.types';
import type { NormalizedDailyMetrics } from './normalized-daily.types';
import type { SourceHealthStatus } from './freshness.types';
import type { AthleteMode } from '../services/health-check/derive-health-check';

export interface AiContextCapability {
  mode: AthleteMode;
  safeFor: string[];
  notSafeFor: string[];
  missingWhoopNativeFields: string[];
  recommendedReadOrder: string[];
}

export interface AiContextBaselines {
  recoveryBaseline: number | null;
  hrvBaseline: number | null;
  restingHrBaseline: number | null;
  sleepBaseline: number | null;
  strainBaseline: number | null;
  dataWindowDays: number;
  computedAt: string;
}

export interface AthleteAiContextResponse {
  ok: boolean;
  athleteId: string;
  date: string;

  /** Seed/live mode flags. */
  seedMode: boolean;
  provisionalUntilDirectWhoop: boolean;
  seedCaveats: string[];

  /** Capability guidance — what the AI is safe to do. */
  capability: AiContextCapability;

  /** Source health — operational truth about data freshness. */
  sourceHealth: SourceHealthStatus | null;

  /** Latest normalized daily metrics (Layer 2, interpretation-free). */
  normalizedDay: NormalizedDailyMetrics | null;

  /** Daily refresh artifact (Layer 3, interpreted). */
  dailyArtifact: DailyRefreshArtifact | null;

  /** Weekly synthesis artifact (Layer 3, weekly rollup). */
  weeklyArtifact: WeeklySynthesisArtifact | null;

  /** Baseline profile from stable memory (Layer 4). */
  baselines: AiContextBaselines | null;

  /** Current block summary from stable memory. */
  blockSummary: string | null;

  /** Nutrition daily summary (deterministic, interpretation-free). */
  nutritionDailySummary: NutritionDailySummary | null;

  /** Nutrition data sources. */
  nutritionSources: string[];

  /** Recent HIIT workout summaries (last 3). */
  recentHIITWorkouts: Array<{
    id: string;
    date: string;
    protocolFormat: string;
    machineType: string;
    totalSets: number;
    avgWatts: number | null;
    totalCalories: number | null;
    avgHr: number | null;
  }> | null;

  /** HIIT progress summary (vs last session). */
  hiitProgressSummary: {
    avgWattsDelta: number | null;
    peakWattsDelta: number | null;
    wattsDropOffPct: number | null;
    hrDriftPct: number | null;
  } | null;

  /** Machine connection status. */
  machineConnectionStatus: {
    hasLiveConnection: boolean;
    primaryFallback: string;
  } | null;

  /** Overall confidence for this context package. */
  confidence: ArtifactConfidence;

  /**
   * Lauburu Readiness — optional grappling-aware readiness score
   * computed by `services/readiness/lauburu-readiness`. Only populated
   * when normalized data depth + sources are sufficient. Coach reads
   * this to surface conservative training-bias guidance; absence
   * means Coach falls back to its existing daily-artifact path.
   *
   * Always experimental. Always not medical advice. The compute
   * module sets these flags on the output object itself.
   */
  lauburu_readiness?: import('../services/readiness/lauburu-readiness').LauburuReadinessOutput | null;
}

/** Compact nutrition summary for prompt-time AI context. */
export interface NutritionDailySummary {
  calories: number | null;
  proteinGrams: number | null;
  carbGrams: number | null;
  fatGrams: number | null;
  /** 'full' | 'partial' | 'none' — deterministic, not athlete-relative. */
  coverage: 'full' | 'partial' | 'none';
  /** Which macros are missing. */
  missingFields: string[];
  /** How the nutrition data was obtained. */
  sourceState: 'live' | 'manual' | 'estimated' | 'mixed' | null;
  /** What sources contributed. */
  sourceDependencies: string[];
  /** Whether all entries were user-confirmed. */
  allConfirmed: boolean;
}
