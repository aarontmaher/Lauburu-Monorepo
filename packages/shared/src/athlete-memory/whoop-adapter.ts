/**
 * WHOOP MCP → DailyMetrics adapter.
 *
 * Converts the WHOOP MCP's get_daily_summary response into the
 * canonical DailyMetrics shape that the athlete-memory refresh
 * pipeline consumes. Pure function, no side effects, no network.
 *
 * Data flow:
 *   WHOOP MCP (get_daily_summary) → WhoopMcpDaySummary[]
 *   → mapWhoopMcpToDailyMetrics() → DailyMetrics[]
 *   → generateAthleteDailyRefresh() → AthleteDailyRefreshArtifact
 *
 * When WHOOP MCP auth is valid, this replaces synthetic/dev-file
 * inputs. When auth is missing or expired, the refresh pipeline
 * should fall back to whatever history is available (HealthKit,
 * manual entries, etc.) — it does not depend on this adapter.
 *
 * Supported metrics from WHOOP MCP daily_summary:
 *   recovery_score, hrv_ms, rhr_bpm, spo2_pct, skin_temp_celsius,
 *   sleep (total, SWS, REM, efficiency, performance, respiratory_rate,
 *   debt, needed baseline, consistency), day_strain, day_kilojoules,
 *   day_avg_hr, day_max_hr, workout_details (sport, strain, HR zones,
 *   duration, calories).
 */

import type { DailyMetrics, Workout } from '../types/health';

// ---------------------------------------------------------------------------
// WHOOP MCP response shape (from get_daily_summary)
// ---------------------------------------------------------------------------

/** Single day from the WHOOP MCP get_daily_summary response. */
export interface WhoopMcpDaySummary {
  local_date: string;
  timezone?: string;

  // Recovery
  recovery_score: number | null;
  hrv_ms: number | null;
  rhr_bpm: number | null;
  spo2_pct: number | null;
  skin_temp_celsius: number | null;

  // Sleep
  sleep_performance_pct: number | null;
  sleep_efficiency_pct: number | null;
  total_sleep_hours: number | null;
  sws_hours: number | null;
  rem_hours: number | null;
  respiratory_rate: number | null;
  sleep_debt_hours: number | null;
  sleep_needed_baseline_hours: number | null;
  sleep_consistency_pct?: number | null;

  // Strain
  day_strain: number | null;
  day_kilojoules: number | null;
  day_avg_hr: number | null;
  day_max_hr: number | null;

  // Workouts
  workout_count: number | null;
  workout_strain_total: number | null;
  workout_minutes_total: number | null;
  workout_details?: WhoopMcpWorkoutDetail[];

  // Metadata
  source_updated_at?: string;
}

/** Single workout from the WHOOP MCP daily_summary. */
export interface WhoopMcpWorkoutDetail {
  id: string;
  sport_id: number;
  sport_name: string;
  strain: number;
  avg_hr: number;
  max_hr: number;
  kilojoules: number;
  calories_kilocalories?: number | null;
  start: string;
  end: string;
  duration_min: number;
  percent_recorded?: number;
  hr_zones?: Array<{
    zone_index: number;
    duration_milli: number;
    percent_of_workout: number;
  }>;
}

// ---------------------------------------------------------------------------
// Grappling sport detection
// ---------------------------------------------------------------------------

const GRAPPLING_SPORT_NAMES = new Set([
  'jiu-jitsu',
  'brazilian-jiu-jitsu',
  'bjj',
  'wrestling',
  'judo',
  'grappling',
  'martial-arts',
]);

function isGrapplingSport(sportName: string): boolean {
  return GRAPPLING_SPORT_NAMES.has(sportName.toLowerCase());
}

function readinessFromRecovery(recovery: number | null): string {
  if (recovery == null) return 'unknown';
  if (recovery >= 67) return 'high';
  if (recovery >= 34) return 'moderate';
  return 'low';
}

// ---------------------------------------------------------------------------
// Adapter
// ---------------------------------------------------------------------------

/**
 * Convert a single WHOOP MCP day summary to the canonical DailyMetrics shape.
 */
export function mapWhoopDayToDailyMetrics(
  day: WhoopMcpDaySummary,
  userId: string = 'default',
): DailyMetrics {
  const workouts: Workout[] = (day.workout_details ?? []).map((w) => ({
    type: w.sport_name,
    sport_label: w.sport_name,
    source: 'WHOOP',
    start_time: w.start,
    end_time: w.end,
    duration_min: w.duration_min,
    strain: w.strain,
    avg_hr: w.avg_hr,
    max_hr: w.max_hr,
    calories:
      w.calories_kilocalories != null
        ? w.calories_kilocalories
        : Math.round(w.kilojoules / 4.184),
    is_grappling: isGrapplingSport(w.sport_name),
    source_id: w.id,
  }));

  // Active calories from kilojoules (rough: total kJ / 4.184)
  const activeCalories =
    day.day_kilojoules != null
      ? Math.round(day.day_kilojoules / 4.184)
      : undefined;

  return {
    user_id: userId,
    date: day.local_date,
    provider: 'whoop',
    recovery_score: day.recovery_score ?? undefined,
    readiness_label: readinessFromRecovery(day.recovery_score),
    hrv_ms: day.hrv_ms ?? undefined,
    resting_hr: day.rhr_bpm ?? undefined,
    sleep_hours: day.total_sleep_hours ?? undefined,
    sleep_performance_pct: day.sleep_performance_pct ?? undefined,
    sleep_efficiency_pct: day.sleep_efficiency_pct ?? undefined,
    sws_hours: day.sws_hours ?? undefined,
    rem_hours: day.rem_hours ?? undefined,
    respiratory_rate: day.respiratory_rate ?? undefined,
    daily_strain: day.day_strain ?? undefined,
    active_calories: activeCalories,
    spo2_pct: day.spo2_pct ?? undefined,
    skin_temp_c: day.skin_temp_celsius ?? undefined,
    workouts: workouts.length > 0 ? workouts : undefined,
    data_source: 'whoop_mcp',
    last_updated: day.source_updated_at,
  };
}

/**
 * Convert an array of WHOOP MCP day summaries to DailyMetrics[].
 * The primary entry point for wiring WHOOP MCP data into the
 * athlete-memory refresh pipeline.
 *
 * Usage:
 * ```typescript
 * // 1. Call WHOOP MCP
 * const whoopResponse = await mcp.get_daily_summary({ days: 30 });
 * const parsed = JSON.parse(whoopResponse.result);
 *
 * // 2. Adapt to DailyMetrics
 * const history = mapWhoopMcpToDailyMetrics(parsed.data, 'athlete-id');
 *
 * // 3. Run athlete refresh
 * const result = generateAthleteDailyRefresh({
 *   athleteId: 'athlete-id',
 *   history,
 * });
 * ```
 */
export function mapWhoopMcpToDailyMetrics(
  days: WhoopMcpDaySummary[],
  userId: string = 'default',
): DailyMetrics[] {
  return days
    .map((day) => mapWhoopDayToDailyMetrics(day, userId))
    .sort((a, b) => a.date.localeCompare(b.date));
}
