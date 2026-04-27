/**
 * AI health sync — posts mobile health data to the canonical
 * backend AI ingestion path after each HealthKit/HC sync.
 *
 * Fire-and-forget: failures are logged but never block the mobile
 * health sync or crash the app. The backend normalizes the data
 * into the canonical athlete-memory AI store.
 *
 * This bridges: mobile HealthKit nativeDays → backend /ingest/health-source/daily
 *
 * Polar-via-Health-Connect provenance:
 * When Health Connect records carry a `source` string indicating Polar
 * Flow (e.g. `com.polar.polarflow`), we additionally post a *second*
 * ingest per affected day with provider=`polar_via_health_connect`
 * containing only the Polar-origin subset of that day's data. The
 * primary `health_connect` ingest still carries the full day (including
 * non-Polar records). This gives the backend two independent
 * source-health rows so source-status questions can answer honestly:
 * "Health Connect is connected" AND "Polar data is coming through
 * Health Connect" — without ever inferring Polar from generic HR shape
 * alone.
 */

import type {
  DailyMetrics,
  RawHealthSample,
  RawWorkoutSample,
  RawSleepSample,
} from '@lauburu/shared';
import { AI_INTERNAL_BASE, AI_INTERNAL_TOKEN } from './ai-backend-config';

const TIMEOUT_MS = 8000;

export interface AiHealthSyncResult {
  attempted: number;
  succeeded: number;
  failed: number;
  errors: string[];
  /** Days on which polar_via_health_connect was additionally ingested. */
  polarViaHcDaysIngested: number;
  /** Detected Polar source app name (e.g. "Polar Flow") or null. */
  polarSourceApp: string | null;
}

/**
 * Known identifiers for Polar Flow across Android (Health Connect
 * `dataOrigin` is a package name) and iOS (Apple Health `source` is a
 * friendly string). Matching is case-insensitive substring.
 *
 * We match on "polar" as a whole token because Polar Flow never changes
 * its brand; false-positive risk (e.g. "polarized" or some unrelated
 * app) is negligible in practice and is further reduced by requiring
 * the package pattern on Android.
 */
const POLAR_SOURCE_PATTERNS: RegExp[] = [
  /(^|[^a-z])polar($|[^a-z])/i, // "Polar", "polar ", "polar_"
  /com\.polar\./i, // Android package pattern
  /polarflow/i,
];

export function isPolarSource(source: string | undefined | null): boolean {
  if (!source) return false;
  return POLAR_SOURCE_PATTERNS.some((re) => re.test(source));
}

/**
 * Detect Concept2/ErgData-origin records in Health Connect. The
 * ErgData app writes workouts to Health Connect under its package name.
 * Concept2 Logbook may also appear as a source when synced.
 */
const CONCEPT2_SOURCE_PATTERNS: RegExp[] = [
  /com\.concept2\./i,
  /ergdata/i,
  /(^|[^a-z])concept\s?2($|[^a-z])/i,
];

export function isConcept2Source(source: string | undefined | null): boolean {
  if (!source) return false;
  return CONCEPT2_SOURCE_PATTERNS.some((re) => re.test(source));
}

/**
 * Samsung Health writes to Health Connect under its package name
 * `com.sec.android.app.shealth` (older) or `com.samsung.android.health`
 * (newer). The dataOrigin string may also be "Samsung Health".
 */
const SAMSUNG_HEALTH_PATTERNS: RegExp[] = [
  /com\.sec\.android\.app\.shealth/i,
  /com\.samsung\.android\.health/i,
  /(^|[^a-z])samsung\s*health($|[^a-z])/i,
];

export function isSamsungHealthSource(source: string | undefined | null): boolean {
  if (!source) return false;
  return SAMSUNG_HEALTH_PATTERNS.some((re) => re.test(source));
}

export function friendlySamsungHealthSourceApp(source: string | undefined | null): string {
  return 'Samsung Health';
}

export function friendlyConcept2SourceApp(source: string | undefined | null): string {
  if (!source) return 'ErgData';
  if (/ergdata/i.test(source)) return 'ErgData';
  return 'Concept2';
}

export function friendlyPolarSourceApp(source: string | undefined | null): string {
  if (!source) return 'Polar Flow';
  // Prefer the common user-facing name; strip Android package prefix.
  if (/com\.polar\./i.test(source)) return 'Polar Flow';
  if (/polarflow/i.test(source)) return 'Polar Flow';
  return 'Polar Flow';
}

export interface RawSamplesByDomain {
  restingHr: RawHealthSample[];
  hrv: RawHealthSample[];
  steps: RawHealthSample[];
  activeCal: RawHealthSample[];
  heartRate: RawHealthSample[];
  workouts: RawWorkoutSample[];
  sleep: RawSleepSample[];
}

function toDay(iso: string | undefined | null): string | null {
  if (!iso) return null;
  return iso.slice(0, 10);
}

interface PolarDayBucket {
  date: string;
  domains: Set<string>;
  workouts: RawWorkoutSample[];
  hrvValues: number[];
  restingHrValues: number[];
  steps: number;
  activeCalories: number;
  sleepMs: number;
  sourceApp: string | null;
  recordIds: string[];
  lastSeenAt: string | null;
}

function bucketFor(buckets: Map<string, PolarDayBucket>, date: string): PolarDayBucket {
  let b = buckets.get(date);
  if (!b) {
    b = {
      date,
      domains: new Set<string>(),
      workouts: [],
      hrvValues: [],
      restingHrValues: [],
      steps: 0,
      activeCalories: 0,
      sleepMs: 0,
      sourceApp: null,
      recordIds: [],
      lastSeenAt: null,
    };
    buckets.set(date, b);
  }
  return b;
}

/** Build one polar_via_health_connect payload per day that has Polar-origin records. */
function buildPolarViaHcPayloads(
  athleteId: string,
  raw: RawSamplesByDomain,
): Array<{ date: string; bucket: PolarDayBucket }> {
  const buckets = new Map<string, PolarDayBucket>();

  const addMetric = (samples: RawHealthSample[], domain: string, reducer: (b: PolarDayBucket, sample: RawHealthSample) => void) => {
    for (const s of samples) {
      if (!isPolarSource(s.source)) continue;
      const date = toDay(s.startDate);
      if (!date) continue;
      const b = bucketFor(buckets, date);
      b.domains.add(domain);
      b.sourceApp ??= friendlyPolarSourceApp(s.source);
      if (!b.lastSeenAt || s.endDate > b.lastSeenAt) b.lastSeenAt = s.endDate;
      reducer(b, s);
    }
  };

  addMetric(raw.restingHr, 'resting_hr', (b, s) => { b.restingHrValues.push(s.value); });
  addMetric(raw.hrv, 'hrv', (b, s) => { b.hrvValues.push(s.value); });
  addMetric(raw.steps, 'steps', (b, s) => { b.steps += s.value; });
  addMetric(raw.activeCal, 'active_calories', (b, s) => { b.activeCalories += s.value; });
  addMetric(raw.heartRate, 'heart_rate_samples', () => { /* presence-only */ });

  // Workouts: group by start date
  for (const w of raw.workouts) {
    if (!isPolarSource(w.source)) continue;
    const date = toDay(w.startDate);
    if (!date) continue;
    const b = bucketFor(buckets, date);
    b.domains.add('workouts');
    if (typeof w.avg_hr === 'number' || typeof w.max_hr === 'number') b.domains.add('workout_hr');
    b.sourceApp ??= friendlyPolarSourceApp(w.source);
    b.workouts.push(w);
    if (w.source_id) b.recordIds.push(w.source_id);
    if (!b.lastSeenAt || w.endDate > b.lastSeenAt) b.lastSeenAt = w.endDate;
  }

  // Sleep: group by end date (a night that ended on date X counts for day X)
  for (const s of raw.sleep) {
    if (!isPolarSource(s.source)) continue;
    const date = toDay(s.endDate) ?? toDay(s.startDate);
    if (!date) continue;
    const b = bucketFor(buckets, date);
    b.domains.add('sleep');
    b.sourceApp ??= friendlyPolarSourceApp(s.source);
    const startMs = new Date(s.startDate).getTime();
    const endMs = new Date(s.endDate).getTime();
    if (Number.isFinite(startMs) && Number.isFinite(endMs) && endMs > startMs) {
      b.sleepMs += endMs - startMs;
    }
    if (!b.lastSeenAt || s.endDate > b.lastSeenAt) b.lastSeenAt = s.endDate;
  }

  return Array.from(buckets.values()).map((bucket) => ({ date: bucket.date, bucket }));
}

function avg(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/**
 * Post an array of DailyMetrics to the backend AI health-source ingest.
 * Each day is posted individually. Failures are collected, not thrown.
 * Returns a summary of what succeeded and what failed.
 *
 * If `raw` is provided, Polar-origin samples within the Health Connect
 * feed are additionally posted as provider=`polar_via_health_connect`.
 * Safe on iOS too — iOS rarely has Polar via HealthKit, and when it
 * does, the same provenance logic applies.
 */
export async function syncHealthToAiBackend(
  athleteId: string,
  days: DailyMetrics[],
  raw?: RawSamplesByDomain,
): Promise<AiHealthSyncResult> {
  if (!AI_INTERNAL_TOKEN || days.length === 0) {
    return { attempted: 0, succeeded: 0, failed: 0, errors: [], polarViaHcDaysIngested: 0, polarSourceApp: null };
  }

  const result: AiHealthSyncResult = {
    attempted: days.length,
    succeeded: 0,
    failed: 0,
    errors: [],
    polarViaHcDaysIngested: 0,
    polarSourceApp: null,
  };

  for (const day of days) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

      const payload = {
        athleteId,
        day: {
          date: day.date,
          provider: day.provider ?? 'apple_health',
          recovery_score: day.recovery_score ?? null,
          hrv_ms: day.hrv_ms ?? null,
          resting_hr: day.resting_hr ?? null,
          sleep_hours: day.sleep_hours ?? null,
          deep_sleep_hours: day.sws_hours ?? null,
          rem_sleep_hours: day.rem_hours ?? null,
          active_calories: day.active_calories ?? null,
          step_count: day.step_count ?? null,
          daily_strain: day.daily_strain ?? null,
          workout_count: day.workouts?.length ?? 0,
          workout_minutes_total: day.workouts
            ? day.workouts.reduce((sum, w) => sum + (w.duration_min ?? 0), 0) || null
            : null,
          grappling_session_count: day.grappling_session ? 1 : 0,
          source_record_ids: day.provider_record_id ? [day.provider_record_id] : [],
          source_updated_at: day.last_updated ?? null,
        },
      };

      const resp = await fetch(`${AI_INTERNAL_BASE}/ingest/health-source/daily`, {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'x-internal-token': AI_INTERNAL_TOKEN,
        },
        body: JSON.stringify(payload),
      });

      clearTimeout(timer);

      if (resp.ok) {
        result.succeeded += 1;
      } else {
        result.failed += 1;
        result.errors.push(`${day.date}: HTTP ${resp.status}`);
      }
    } catch (e) {
      result.failed += 1;
      result.errors.push(`${day.date}: ${e instanceof Error ? e.message : 'unknown'}`);
    }
  }

  // Second pass: if raw samples were provided, post polar_via_health_connect
  // ingests for every day that had Polar-origin records.
  if (raw) {
    const polarPayloads = buildPolarViaHcPayloads(athleteId, raw);
    for (const { date, bucket } of polarPayloads) {
      if (bucket.domains.size === 0) continue;
      if (!result.polarSourceApp && bucket.sourceApp) result.polarSourceApp = bucket.sourceApp;
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
        const workoutMinutes = bucket.workouts.reduce((s, w) => s + (w.duration_min ?? 0), 0);
        const hrvMs = avg(bucket.hrvValues);
        const restingHr = avg(bucket.restingHrValues);
        const sleepHours = bucket.sleepMs > 0 ? bucket.sleepMs / 3_600_000 : null;

        const polarPayload = {
          athleteId,
          day: {
            date,
            provider: 'polar_via_health_connect' as const,
            recovery_score: null, // Polar via HC never exposes recovery
            hrv_ms: hrvMs,
            resting_hr: restingHr,
            sleep_hours: sleepHours,
            deep_sleep_hours: null,
            rem_sleep_hours: null,
            active_calories: bucket.activeCalories > 0 ? bucket.activeCalories : null,
            step_count: bucket.steps > 0 ? bucket.steps : null,
            daily_strain: null, // Polar via HC never exposes strain
            workout_count: bucket.workouts.length,
            workout_minutes_total: workoutMinutes > 0 ? workoutMinutes : null,
            grappling_session_count: 0,
            source_record_ids: bucket.recordIds,
            source_updated_at: bucket.lastSeenAt,
            source_app: bucket.sourceApp,
            domains_from_polar: Array.from(bucket.domains),
          },
        };

        const resp = await fetch(`${AI_INTERNAL_BASE}/ingest/health-source/daily`, {
          method: 'POST',
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            'x-internal-token': AI_INTERNAL_TOKEN,
          },
          body: JSON.stringify(polarPayload),
        });

        clearTimeout(timer);

        if (resp.ok) {
          result.polarViaHcDaysIngested += 1;
        } else {
          result.errors.push(`polar_via_hc ${date}: HTTP ${resp.status}`);
        }
      } catch (e) {
        result.errors.push(`polar_via_hc ${date}: ${e instanceof Error ? e.message : 'unknown'}`);
      }
    }
  }

  if (result.failed > 0 || result.polarViaHcDaysIngested > 0) {
    console.log(
      '[AI-SYNC]',
      `${result.succeeded}/${result.attempted} days synced, ${result.failed} failed, ${result.polarViaHcDaysIngested} polar-via-HC days` + (result.polarSourceApp ? ` (${result.polarSourceApp})` : ''),
      result.errors.slice(0, 3),
    );
  }

  return result;
}
