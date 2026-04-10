/**
 * WHOOP store — read-only surface of the backend-fed WHOOP day record.
 *
 * Architecture notes:
 * - Ingestion happens in the Railway WHOOP MCP service. This store does not
 *   authenticate against WHOOP directly and does not hold tokens.
 * - Data is fetched through the existing Supabase edge function
 *   `whoop-bridge` at `/data/today`, which is a thin CORS proxy to Railway.
 *   The same path the website uses from `refreshWhoopFromBackend()`.
 * - This store is purely a display/freshness cache. No writes, no mutations
 *   of backend state, no OAuth flows.
 * - Honesty: if the upstream payload is missing fields, we leave them null
 *   rather than faking values. The renderer decides how to present gaps.
 */
import { create } from 'zustand';
import { SUPABASE_FUNCTIONS_URL, SUPABASE_ANON_KEY } from '@lauburu/shared';

const WHOOP_BRIDGE_URL = `${SUPABASE_FUNCTIONS_URL}/whoop-bridge?path=${encodeURIComponent('/data/today')}`;

/** Normalized WHOOP day object as rendered in the mobile app. */
export interface WhoopDay {
  /** Local WHOOP cycle date (YYYY-MM-DD). */
  date: string;
  /** Recovery score 0–100. Null if not finalised yet. */
  recovery_score: number | null;
  /** HRV in milliseconds. */
  hrv_ms: number | null;
  /** Resting heart rate (bpm). */
  resting_hr: number | null;
  /** Total sleep in hours. */
  sleep_hours: number | null;
  /** Sleep performance percentage. */
  sleep_performance_pct: number | null;
  /** Whole-day strain 0–21. */
  daily_strain: number | null;
  /** Workout summaries for the day (may be empty even when recovery is present). */
  workouts: WhoopWorkout[];
  /**
   * Upstream freshness timestamp from the WHOOP MCP ingest layer.
   * Distinct from `fetchedAt` — this is when the Railway service last
   * refreshed the day row from WHOOP's API, not when the app fetched it.
   */
  source_updated_at: string | null;
}

export interface WhoopWorkout {
  sport_name?: string;
  sport_id?: number;
  strain?: number;
  start?: string;
  end?: string;
  duration_min?: number;
}

type WhoopStatus = 'idle' | 'loading' | 'ready' | 'error';

interface WhoopState {
  status: WhoopStatus;
  day: WhoopDay | null;
  /** When the app last successfully fetched (client-local ISO). */
  fetchedAt: string | null;
  error: string | null;

  fetchToday: () => Promise<void>;
}

/**
 * Unwrap whatever envelope Railway returns. Matches index.html:2819 logic
 * so we behave identically to the website.
 */
function unwrap(payload: any): any {
  if (!payload || typeof payload !== 'object') return null;
  return payload.latest_day ?? payload.data ?? payload.today ?? payload;
}

/**
 * Pure normalizer. Mirrors website `normalizeWhoopDailyForApp` but keeps
 * `source_updated_at` from the raw record so the UI can show staleness.
 */
function normalize(raw: any): WhoopDay | null {
  const src = unwrap(raw);
  if (!src || src.error) return null;

  const date: string | undefined = src.date ?? src.local_date;
  if (!date) return null;

  const recovery = src.recovery ?? {};
  const strain = src.strain ?? {};
  const sleep = src.sleep ?? {};

  const rawWorkouts: any[] = Array.isArray(src.workouts)
    ? src.workouts
    : Array.isArray(src.workout_list)
      ? src.workout_list
      : Array.isArray(src.activities)
        ? src.activities
        : [];

  const workouts: WhoopWorkout[] = rawWorkouts.map((w) => ({
    sport_name: w?.sport_name,
    sport_id: w?.sport_id,
    strain: w?.strain ?? w?.score,
    start: w?.start,
    end: w?.end,
    duration_min: w?.duration_min,
  }));

  return {
    date,
    recovery_score:
      recovery.score != null ? recovery.score : src.recovery_score ?? null,
    hrv_ms: recovery.hrv_ms != null ? recovery.hrv_ms : src.hrv_ms ?? null,
    resting_hr:
      recovery.rhr_bpm != null ? recovery.rhr_bpm : src.resting_hr ?? null,
    sleep_hours:
      sleep.total_hours != null ? sleep.total_hours : src.sleep_hours ?? null,
    sleep_performance_pct:
      sleep.performance_pct != null
        ? sleep.performance_pct
        : src.sleep_performance_pct ?? null,
    daily_strain:
      strain.day_strain != null ? strain.day_strain : src.daily_strain ?? null,
    workouts,
    source_updated_at: src.source_updated_at ?? src.updated_at ?? null,
  };
}

export const useWhoopStore = create<WhoopState>((set) => ({
  status: 'idle',
  day: null,
  fetchedAt: null,
  error: null,

  fetchToday: async () => {
    set({ status: 'loading', error: null });
    try {
      // Note: whoop-bridge has verify_jwt=false so this anon-key header is
      // purely to satisfy Supabase's default function ingress. No user JWT
      // is required — we are reading backend-canonical WHOOP data that is
      // already de-identified at this layer.
      const resp = await fetch(WHOOP_BRIDGE_URL, {
        method: 'GET',
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          Accept: 'application/json',
        },
      });
      if (!resp.ok) {
        set({
          status: 'error',
          error: `WHOOP bridge returned HTTP ${resp.status}`,
          fetchedAt: new Date().toISOString(),
        });
        return;
      }
      const payload = await resp.json();
      const day = normalize(payload);
      if (!day) {
        set({
          status: 'error',
          error: 'WHOOP payload could not be normalized',
          fetchedAt: new Date().toISOString(),
        });
        return;
      }
      set({
        status: 'ready',
        day,
        fetchedAt: new Date().toISOString(),
        error: null,
      });
    } catch (e: any) {
      set({
        status: 'error',
        error: e?.message ?? 'WHOOP fetch failed',
        fetchedAt: new Date().toISOString(),
      });
    }
  },
}));
