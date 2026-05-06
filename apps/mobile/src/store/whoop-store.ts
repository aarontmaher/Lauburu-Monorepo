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

/**
 * Normalized WHOOP day object as rendered in the mobile app.
 * Structurally compatible with `@lauburu/shared` `WhoopSnapshot` so it can
 * be passed directly into `buildDailyCoachingBrief()` without conversion.
 */
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
  /** Derived workout count — convenience mirror of `workouts.length`. */
  workout_count: number;
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
 *
 * `envelope` is the full decoded response body (before unwrap). Some Railway
 * payload shapes surface freshness at the envelope level rather than inside
 * the day object, so we check both.
 */
function normalize(raw: any): WhoopDay | null {
  const envelope: any = raw ?? {};
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
    workout_count: workouts.length,
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
    // Upstream freshness: try every plausible field name the Railway MCP /
    // WHOOP schema might expose, checking the envelope (response root) first
    // and the unwrapped day object second. The MCP daily_summary response
    // surfaces source_updated_at at the envelope level for some shapes.
    source_updated_at:
      envelope.source_updated_at ??
      envelope.updated_at ??
      envelope.last_updated ??
      envelope.cycle_updated_at ??
      envelope.as_of ??
      envelope.synced_at ??
      src.source_updated_at ??
      src.updated_at ??
      src.last_updated ??
      src.cycle_updated_at ??
      src.as_of ??
      src.synced_at ??
      null,
  };
}

export const useWhoopStore = create<WhoopState>((set) => ({
  status: 'idle',
  day: null,
  fetchedAt: null,
  error: null,

  fetchToday: async () => {
    // Always flip to 'loading' first so every Refresh tap produces
    // visible feedback — without this, a user stuck in the non-owner
    // error state taps Refresh and sees nothing change (the resulting
    // error text is identical to what's already on screen), making
    // the button feel dead. One frame of spinner is plenty.
    set({ status: 'loading', error: null });
    // Give React a tick to render the spinner before we block on the
    // owner check. Otherwise the synchronous ownership resolution can
    // race the state flip on fast devices.
    await new Promise((r) => setTimeout(r, 50));
    // CRITICAL: only fetch the bridge if the current user owns the WHOOP connection.
    // The Supabase bridge is a single-user proxy; displaying its data to a non-owner
    // would leak Aaron's WHOOP data to other accounts (e.g. girlfriend's account).
    const { useAuthStore } = require('./auth-store');
    const userId = useAuthStore.getState().user?.id as string | undefined;
    const ownershipMod = require('../services/whoop-ownership');
    const { isWhoopBridgeOwner, whoopBridgeOwnerCount, whoopBridgeOwnerSources } = ownershipMod;
    if (!isWhoopBridgeOwner(userId)) {
      const count = typeof whoopBridgeOwnerCount === 'function' ? whoopBridgeOwnerCount() : 0;
      const sources = typeof whoopBridgeOwnerSources === 'function' ? whoopBridgeOwnerSources() : [];
      // Previously set status='ready' + day=null silently, which made
      // the card render as "partial: missing recovery/HRV/RHR/sleep/
      // workouts" with no reason given. Keep the normal UI honest
      // without exposing owner allowlist details or user IDs.
      set({
        status: 'error',
        day: null,
        fetchedAt: new Date().toISOString(),
        error: userId
          ? `WHOOP Direct is not linked to this account yet. Ask Aaron to add this account to the WHOOP bridge allowlist. Config sources detected: ${count} (${sources.join('+') || 'none'}).`
          : 'WHOOP Direct: sign in first, then ask Aaron to link this account if you use WHOOP.',
      });
      return;
    }
    // Already set status='loading' above — no need to flip again.
    try {
      const resp = await fetch(WHOOP_BRIDGE_URL, {
        method: 'GET',
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          Accept: 'application/json',
        },
      });
      if (!resp.ok) {
        const label = resp.status === 504 ? 'WHOOP bridge timed out'
          : resp.status === 502 ? 'WHOOP bridge unavailable'
          : `WHOOP bridge returned HTTP ${resp.status}`;
        set((prev) => ({
          status: 'error',
          // Preserve existing day data so the card can show "Using last available data"
          day: prev.day,
          error: label,
          fetchedAt: new Date().toISOString(),
        }));
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
      const msg = e?.name === 'AbortError' ? 'WHOOP bridge timed out'
        : e?.message ?? 'WHOOP fetch failed';
      set((prev) => ({
        status: 'error',
        day: prev.day, // preserve cached data
        error: msg,
        fetchedAt: new Date().toISOString(),
      }));
    }
  },
}));
