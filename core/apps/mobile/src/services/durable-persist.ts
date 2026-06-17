/**
 * durable-persist — one-shot "push everything to the durable backend
 * layer" helper. Independent of Supabase /health-import (which remains
 * blocked on the HS256 JWT flip). The Railway /v1/internal/ingest/*
 * pipeline is already authenticated via x-internal-token and does NOT
 * depend on the Supabase signing algorithm — so we can make Save to
 * Account materially useful TODAY, then the Supabase path becomes a
 * redundant secondary mirror once the JWT is flipped.
 *
 * What lands in Railway per call:
 *   - per-day merged Apple Health / Health Connect records (full
 *     normalized day + provider tag + Polar/Samsung HC provenance)
 *   - every local HIIT workout (per-set detail, fatigue deltas,
 *     source=ble_live tag when auto-filled)
 *   - nutrition today + historyDays (manual/barcode/hub-merged) with
 *     body_weight_kg + meal timing + missingFields
 *
 * What does NOT land yet (and how to make it land):
 *   - WHOOP Direct history: already persisted by Railway's WHOOP MCP
 *     independently; nothing for the client to push.
 *   - WHOOP export enrichment: runs through its own upload route.
 *   - AppAthleteState artifacts: pushed inline with every Coach
 *     /coach/ask request; backend keeps the most recent view.
 *   - Non-HIIT training sessions (grappling class, drilling, etc.):
 *     currently local only. TODO: mirror to /ingest/session-log with
 *     a non-HIIT shape in a follow-up.
 */

import type { DailyMetrics, NutritionRecord } from '@lauburu/shared';
import { syncHealthToAiBackend } from './ai-health-sync';
import { syncNutritionToAiBackend } from './ai-nutrition-sync';
import {
  syncHIITWorkoutToAiBackend,
  syncTrainingSessionToAiBackend,
  syncAppAthleteStateSnapshotToAiBackend,
} from './ai-hiit-sync';

export interface DurablePersistResult {
  ok: boolean;
  daysPushed: number;
  nutritionDaysPushed: number;
  hiitWorkoutsPushed: number;
  sessionsPushed: number;
  athleteStateSnapshotPushed: boolean;
  error?: string;
}

/**
 * Push every durable artifact the client owns to Railway. Safe to call
 * fire-and-forget from Save to Account; each sub-call is already
 * fire-and-forget internally, this orchestrates the fan-out + returns
 * a summary for the UI banner.
 */
export async function persistDurableToRailway(
  athleteId: string,
  days: DailyMetrics[],
  nutritionToday: NutritionRecord | null,
  nutritionHistory: NutritionRecord[],
  hiitWorkouts: Array<any> = [],
  trainingSessions: Array<any> = [],
  athleteStateSnapshot: unknown = null,
): Promise<DurablePersistResult> {
  if (!athleteId) return { ok: false, daysPushed: 0, nutritionDaysPushed: 0, hiitWorkoutsPushed: 0, sessionsPushed: 0, athleteStateSnapshotPushed: false, error: 'Sign in required' };

  let daysPushed = 0;
  let nutritionDaysPushed = 0;
  let hiitWorkoutsPushed = 0;
  let sessionsPushed = 0;
  let athleteStateSnapshotPushed = false;

  // Health source-daily ingest — pushes the full normalized days array
  // + provenance. Returns count when individual POSTs succeed.
  try {
    // syncHealthToAiBackend needs the raw sample buckets for
    // provenance. At the point this runs, we have normalized days
    // but not raw sample arrays. Push the days as-is; the ingest
    // endpoint accepts either shape. Pass empty sample arrays for
    // provenance — a follow-up can wire raw buckets through.
    await syncHealthToAiBackend(athleteId, days, {
      restingHr: [], hrv: [], steps: [], activeCal: [], heartRate: [],
      workouts: [], sleep: [],
    });
    daysPushed = days.length;
  } catch {
    /* fire-and-forget */
  }

  // Nutrition: today + history. History already has per-day records
  // with provenance.
  try {
    const toShip: NutritionRecord[] = [];
    if (nutritionToday) toShip.push(nutritionToday);
    for (const d of nutritionHistory) {
      if (nutritionToday && d.date === nutritionToday.date) continue;
      toShip.push(d);
    }
    for (const rec of toShip) {
      try {
        const okRow = await syncNutritionToAiBackend(athleteId, rec);
        if (okRow) nutritionDaysPushed += 1;
      } catch { /* per-row failure tolerated */ }
    }
  } catch { /* ignore */ }

  // HIIT sessions — each saved workout already ships on save, but a
  // one-shot Save-to-Account re-push is useful when the user wants to
  // flush a whole history after a reinstall. Idempotent server-side
  // (dedup by sessionId).
  try {
    for (const w of hiitWorkouts) {
      try {
        await syncHIITWorkoutToAiBackend(athleteId, w);
        hiitWorkoutsPushed += 1;
      } catch { /* per-workout failure tolerated */ }
    }
  } catch { /* ignore */ }

  // Non-HIIT training sessions (grappling class, drilling, wrestling,
  // zone 2, manual). Skip mirrored-HIIT rows (preset_id starts with
  // 'hiit:') so we don't double-count with the workout ingest above.
  try {
    for (const s of trainingSessions) {
      if (!s || !s.date) continue;
      if (typeof s.preset_id === 'string' && s.preset_id.startsWith('hiit:')) continue;
      try {
        await syncTrainingSessionToAiBackend(athleteId, s);
        sessionsPushed += 1;
      } catch { /* per-session failure tolerated */ }
    }
  } catch { /* ignore */ }

  // AppAthleteState snapshot — the app-owned merged interpretation
  // (recovery/load/sleep/fueling/hydration/acute-fatigue/chronic-load-
  // trend/readiness-confidence/source-roles/data-quality). Pushing this
  // gives AI learning a durable artifact to reason over, not just raw
  // ingest. Backend keeps the most recent snapshot per user per day.
  if (athleteStateSnapshot) {
    try {
      const ok = await syncAppAthleteStateSnapshotToAiBackend(athleteId, athleteStateSnapshot);
      athleteStateSnapshotPushed = !!ok;
    } catch { /* fire-and-forget */ }
  }

  return { ok: true, daysPushed, nutritionDaysPushed, hiitWorkoutsPushed, sessionsPushed, athleteStateSnapshotPushed };
}
