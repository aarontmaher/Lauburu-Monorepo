/**
 * Exportable AI payload — compact, deterministic, inspectable.
 *
 * This is the single function that produces a serializable JSON payload
 * suitable for:
 * - MCP-backed coaching prompts
 * - Daily recommendation generation
 * - Habit/training analysis
 * - Export for debugging / inspection
 *
 * The payload is designed so an LLM or rules engine can produce training
 * guidance from it without needing access to the raw health store.
 *
 * Future coaching insertion points:
 * ─────────────────────────────────
 * 1. MCP coaching prompt:
 *    const payload = exportAIPayload(days, features, flags, insights);
 *    await mcpCall('generate_coaching', { context: payload });
 *
 * 2. Daily recommendation (cron/background):
 *    const payload = exportAIPayload(...);
 *    const rec = await fetch(MCP_API + '/daily-recommendation', {
 *      body: JSON.stringify(payload)
 *    });
 *
 * 3. Source-specific enrichment:
 *    When WHOOP/ErgZone/Cronometer is connected, their data flows through
 *    DailyMetrics normalization → deriveFeatures → insights → this payload.
 *    No changes to this function are needed — richer data produces richer
 *    features automatically.
 *
 * 4. Grappling-specific coaching:
 *    payload.training_context.grappling_sessions carries session count.
 *    payload.training_context.recent_grappling lists grappling workouts.
 *    A future coach layer can use these to suggest technique focus areas
 *    based on recovery state + training frequency.
 */
import type { DailyMetrics, DerivedFeatures } from '../types/health';
import type { AIHealthContext } from './ai-context';
import type { TrainingInsight } from './insights';
import type { HealthFlag } from './derive-features';

/**
 * Exportable AI payload — everything needed for coaching/analysis
 * in one serializable object.
 */
export interface AIPayload {
  /** Schema version for forward compatibility */
  version: 1;

  /** When this payload was generated */
  generated_at: string;

  /** Sync freshness */
  sync: {
    last_native_sync: string | null;
    last_backend_persist: string | null;
    data_age_hours: number | null;
  };

  /** Data quality summary */
  coverage: {
    days_available: number;
    providers: string[];
    has_today: boolean;
    has_sleep: boolean;
    has_hrv: boolean;
    has_recovery: boolean;
    has_workouts: boolean;
    has_grappling: boolean;
    has_nutrition: boolean;
    has_subjective: boolean;
  };

  /** Today's readiness assessment */
  readiness: {
    level: TrainingInsight['readiness'];
    label: string;
    recommendation: string;
    reasons: string[];
  };

  /** Key metrics snapshot */
  metrics: TrainingInsight['key_metrics'];

  /** Signals */
  positives: string[];
  concerns: string[];

  /** Trends */
  trends: AIHealthContext['trends'];

  /** Training context for grappling-specific coaching */
  training_context: {
    workouts_7d: number;
    grappling_sessions_7d: number;
    rest_days_7d: number;
    consecutive_training_days: number;
    avg_strain_7d: number | null;
    avg_sleep_7d: number | null;
    recent_grappling: Array<{
      date: string;
      duration_min: number;
      source?: string;
    }>;
  };

  /** Baselines for personalization */
  baselines: AIHealthContext['baselines'];

  /** Pre-computed flags */
  flags: Array<{ type: string; label: string }>;
}

/**
 * Export the complete AI payload from current state.
 */
export function exportAIPayload(
  days: DailyMetrics[],
  features: DerivedFeatures,
  flags: HealthFlag[],
  insights: TrainingInsight,
  aiContext: AIHealthContext,
  lastSyncAt: string | null,
  lastPersistedAt: string | null,
): AIPayload {
  const sorted = [...days].sort((a, b) => a.date.localeCompare(b.date));
  const last7 = sorted.slice(-7);

  // Consecutive training days (counting backward from today)
  let consecutiveTraining = 0;
  for (let i = sorted.length - 1; i >= 0; i--) {
    const d = sorted[i];
    if (d.workouts?.length || d.grappling_session) {
      consecutiveTraining++;
    } else {
      break;
    }
  }

  // Recent grappling sessions
  const recentGrappling: AIPayload['training_context']['recent_grappling'] = [];
  for (const day of last7) {
    for (const w of day.workouts ?? []) {
      if (w.is_grappling) {
        recentGrappling.push({
          date: day.date,
          duration_min: w.duration_min,
          source: w.source,
        });
      }
    }
    if (day.grappling_session) {
      recentGrappling.push({
        date: day.date,
        duration_min: day.grappling_session.duration_min,
      });
    }
  }

  // Data age
  const dataAgeHours = lastSyncAt
    ? Math.round(
        (Date.now() - new Date(lastSyncAt).getTime()) / 3_600_000 * 10,
      ) / 10
    : null;

  return {
    version: 1,
    generated_at: new Date().toISOString(),

    sync: {
      last_native_sync: lastSyncAt,
      last_backend_persist: lastPersistedAt,
      data_age_hours: dataAgeHours,
    },

    coverage: {
      days_available: days.length,
      providers: features.provenance,
      has_today: aiContext.today != null,
      has_sleep: !features.missing.sleep_data,
      has_hrv: !features.missing.hrv_data,
      has_recovery: features.baseline_recovery_mean != null,
      has_workouts: !features.missing.workout_detail,
      has_grappling: !features.missing.grappling_sessions,
      has_nutrition: sorted.some((d) => d.nutrition != null),
      has_subjective: !features.missing.subjective_data,
    },

    readiness: {
      level: insights.readiness,
      label: insights.readiness_label,
      recommendation: insights.recommendation.summary,
      reasons: insights.recommendation.reasons,
    },

    metrics: insights.key_metrics,
    positives: insights.positives,
    concerns: insights.concerns,

    trends: aiContext.trends,

    training_context: {
      workouts_7d: aiContext.recent_7d.workout_count,
      grappling_sessions_7d: aiContext.recent_7d.grappling_count,
      rest_days_7d: aiContext.recent_7d.rest_days,
      consecutive_training_days: consecutiveTraining,
      avg_strain_7d: aiContext.recent_7d.strain_mean,
      avg_sleep_7d: aiContext.recent_7d.sleep_mean,
      recent_grappling: recentGrappling,
    },

    baselines: aiContext.baselines,

    flags: flags.map((f) => ({ type: f.type, label: f.label })),
  };
}
