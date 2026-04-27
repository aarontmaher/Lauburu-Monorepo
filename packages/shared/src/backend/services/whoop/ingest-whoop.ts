/**
 * WHOOP raw ingestion — converts MCP daily_summary responses
 * into typed WhoopDailyMetricsRaw records for Layer 1 storage.
 *
 * Pure function. No network calls. No interpretation.
 * Preserves data exactly as received; missing stays null.
 *
 * Internal-only: called by /v1/internal/ingest/whoop, never
 * by client-facing app routes.
 */

import type {
  WhoopDailyMetricsRaw,
  WhoopRawWorkout,
  WhoopRawHrZone,
} from '../../contracts/whoop-raw.types';

/** Shape of a single day from the WHOOP MCP get_daily_summary. */
export interface WhoopMcpDayPayload {
  local_date: string;
  timezone?: string;
  recovery_score: number | null;
  hrv_ms: number | null;
  rhr_bpm: number | null;
  spo2_pct: number | null;
  skin_temp_celsius: number | null;
  sleep_performance_pct: number | null;
  sleep_efficiency_pct: number | null;
  total_sleep_hours: number | null;
  sws_hours: number | null;
  rem_hours: number | null;
  light_sleep_hours?: number | null;
  awake_hours?: number | null;
  in_bed_hours?: number | null;
  respiratory_rate: number | null;
  sleep_debt_hours: number | null;
  sleep_needed_baseline_hours: number | null;
  sleep_consistency_pct?: number | null;
  day_strain: number | null;
  day_kilojoules: number | null;
  day_avg_hr: number | null;
  day_max_hr: number | null;
  workout_count: number | null;
  workout_strain_total: number | null;
  workout_minutes_total: number | null;
  workout_details?: Array<{
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
    percent_recorded?: number | null;
    hr_zones?: Array<{
      zone_index: number;
      duration_milli: number;
      percent_of_workout: number;
    }>;
  }>;
  source_updated_at?: string;
  cycle_id?: number | null;
  sleep_id?: string | null;
  recovery_cycle_id?: number | null;
}

let _idCounter = 0;
function generateId(prefix: string, date: string): string {
  return `${prefix}_${date}_${Date.now()}_${++_idCounter}`;
}

/**
 * Convert one WHOOP MCP day payload into a typed raw record.
 * Pure, deterministic (except for id generation timestamps).
 */
export function ingestWhoopDay(
  payload: WhoopMcpDayPayload,
  athleteId: string,
): WhoopDailyMetricsRaw {
  const now = new Date().toISOString();

  const workoutDetails: WhoopRawWorkout[] = (payload.workout_details ?? []).map((w) => ({
    id: w.id,
    sportId: w.sport_id,
    sportName: w.sport_name,
    strain: w.strain,
    avgHr: w.avg_hr,
    maxHr: w.max_hr,
    kilojoules: w.kilojoules,
    caloriesKcal: w.calories_kilocalories ?? null,
    startIso: w.start,
    endIso: w.end,
    durationMin: w.duration_min,
    percentRecorded: w.percent_recorded ?? null,
    hrZones: (w.hr_zones ?? []).map((z): WhoopRawHrZone => ({
      zoneIndex: z.zone_index,
      durationMilli: z.duration_milli,
      percentOfWorkout: z.percent_of_workout,
    })),
  }));

  return {
    id: generateId('whoop_raw', payload.local_date),
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    athleteId,
    localDate: payload.local_date,
    timezone: payload.timezone ?? 'UTC',
    recoveryScore: payload.recovery_score,
    hrvMs: payload.hrv_ms,
    rhrBpm: payload.rhr_bpm,
    spo2Pct: payload.spo2_pct,
    skinTempCelsius: payload.skin_temp_celsius,
    sleepPerformancePct: payload.sleep_performance_pct,
    sleepEfficiencyPct: payload.sleep_efficiency_pct,
    totalSleepHours: payload.total_sleep_hours,
    swsHours: payload.sws_hours,
    remHours: payload.rem_hours,
    lightSleepHours: payload.light_sleep_hours ?? null,
    awakeHours: payload.awake_hours ?? null,
    inBedHours: payload.in_bed_hours ?? null,
    respiratoryRate: payload.respiratory_rate,
    sleepDebtHours: payload.sleep_debt_hours,
    sleepNeededBaselineHours: payload.sleep_needed_baseline_hours,
    sleepConsistencyPct: payload.sleep_consistency_pct ?? null,
    dayStrain: payload.day_strain,
    dayKilojoules: payload.day_kilojoules,
    dayAvgHr: payload.day_avg_hr,
    dayMaxHr: payload.day_max_hr,
    workoutCount: payload.workout_count ?? 0,
    workoutStrainTotal: payload.workout_strain_total,
    workoutMinutesTotal: payload.workout_minutes_total,
    workoutDetails,
    sourceUpdatedAt: payload.source_updated_at ?? null,
    sourceRecordIds: {
      cycleId: payload.cycle_id ?? null,
      sleepId: payload.sleep_id ?? null,
      recoveryCycleId: payload.recovery_cycle_id ?? null,
    },
  };
}

/**
 * Ingest a batch of WHOOP MCP day payloads.
 * Returns typed raw records sorted by date ascending.
 */
export function ingestWhoopBatch(
  payloads: WhoopMcpDayPayload[],
  athleteId: string,
): WhoopDailyMetricsRaw[] {
  return payloads
    .map((p) => ingestWhoopDay(p, athleteId))
    .sort((a, b) => a.localDate.localeCompare(b.localDate));
}
