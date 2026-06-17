/**
 * Convert normalized DailyMetrics[] to the shape expected by
 * POST /health-import edge function.
 *
 * The backend expects: { provider, import_mode, raw_payload: Record[] }
 * where each record has flat metric fields keyed by date.
 *
 * Future data source insertion points:
 * - ErgZone: call persistHealthData() with provider='ergzone' and
 *   records containing detailed workout payloads in raw_payload
 * - Cronometer: call with provider='cronometer' and nutrition fields
 * - WHOOP: already handled by website backend; mobile could also
 *   call this with provider='whoop' for direct sync
 */
import type { DailyMetrics } from '../types/health';

/** Convert DailyMetrics to the flat record shape the backend expects */
export function toBackendPayload(
  days: DailyMetrics[],
): Record<string, unknown>[] {
  return days
    .filter((d) => d.date) // must have a date
    .map((d) => ({
      date: d.date,
      recovery_score: d.recovery_score ?? null,
      readiness_label: d.readiness_label ?? null,
      hrv_ms: d.hrv_ms != null ? Math.round(d.hrv_ms) : null,
      resting_hr: d.resting_hr != null ? Math.round(d.resting_hr) : null,
      sleep_hours:
        d.sleep_hours != null
          ? Math.round(d.sleep_hours * 100) / 100
          : null,
      sleep_performance_pct: d.sleep_performance_pct ?? null,
      daily_strain:
        d.daily_strain != null
          ? Math.round(d.daily_strain * 10) / 10
          : null,
      step_count: d.step_count != null ? Math.round(d.step_count) : null,
    }));
}
