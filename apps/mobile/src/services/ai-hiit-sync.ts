/**
 * Fire-and-forget HIIT workout sync to AI backend.
 * Mirrors ai-nutrition-sync.ts pattern — never blocks, never throws.
 *
 * Converts the mobile HIITWorkoutRecord into a SessionLogIngestPayload
 * compatible with POST /v1/internal/ingest/session-log.
 */
import type { HIITWorkoutRecord } from '@lauburu/shared';
import { AI_INTERNAL_BASE, AI_INTERNAL_TOKEN } from './ai-backend-config';

export async function syncHIITWorkoutToAiBackend(
  athleteId: string,
  workout: HIITWorkoutRecord,
): Promise<void> {
  if (!AI_INTERNAL_TOKEN) return;
  try {
    // Convert HIITWorkoutRecord → SessionLogIngestPayload
    const session = {
      sessionId: workout.id,
      athleteId,
      date: workout.date,
      createdAt: workout.createdAt,
      templateId: workout.templateId,
      protocolFormat: workout.protocolFormat,
      machineType: workout.machineType,
      machineProvider: workout.machineProvider,
      source: workout.source === 'manual' ? 'manual' : workout.source,
      sets: workout.sets.map((s) => ({
        ...s,
        hrAtStart: null,
        hrAtEnd: null,
        hrRange: s.hrMax != null && s.hrMin != null ? s.hrMax - s.hrMin : null,
        hrRecoveryFromPrevious: null,
      })),
      totalSets: workout.totalSets,
      workSets: workout.workSets,
      restSets: workout.restSets,
      totalDurationSeconds: workout.totalDurationSeconds,
      totalCalories: workout.totalCalories,
      totalWorkKj: workout.totalWorkKj,
      avgWatts: workout.avgWatts,
      peakWatts: workout.peakWatts,
      avgHr: workout.avgHr,
      peakHr: workout.peakHr,
      sourceRecordIds: workout.sourceRecordIds,
      missingFields: workout.missingFields,
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    await fetch(`${AI_INTERNAL_BASE}/ingest/session-log`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-internal-token': AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({ athleteId, session }),
      signal: controller.signal,
    });
    clearTimeout(timer);
  } catch {
    // Fire-and-forget — failures never surface to the user.
  }
}

/**
 * AppAthleteState snapshot ingest. Pushes the app-owned merged
 * athlete-state (recovery/load/sleep/fueling/hydration/acute-fatigue/
 * chronic-load-trend/readiness-confidence/source-roles/data-quality)
 * to the backend so AI learning has a durable artifact to reason
 * over — not just raw ingest data. Survives reinstall because the
 * backend keeps the latest snapshot per-user per-date.
 *
 * Fire-and-forget. Called when Save to Account runs OR whenever the
 * state materially changes (we throttle to avoid spamming).
 */
export async function syncAppAthleteStateSnapshotToAiBackend(
  athleteId: string,
  snapshot: unknown,
): Promise<boolean> {
  if (!AI_INTERNAL_TOKEN || !athleteId || !snapshot) return false;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const res = await fetch(`${AI_INTERNAL_BASE}/ingest/athlete-state/snapshot`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-internal-token': AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({ athleteId, snapshot, capturedAt: new Date().toISOString() }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    return !!res?.ok;
  } catch {
    // fire-and-forget; backend may 404 until route is deployed
    return false;
  }
}

/**
 * Non-HIIT training session ingest. Grappling class, drilling,
 * wrestling, zone 2, manual workouts — everything the user logs from
 * Train that isn't a HIIT protocol. Previously these were local-only;
 * now they ship to the same /ingest/session-log endpoint with a
 * generic session shape so backend trend logic sees the full training
 * history, not just HIIT days.
 */
export async function syncTrainingSessionToAiBackend(
  athleteId: string,
  session: {
    id?: string;
    created_at?: string;
    date: string;
    type: string;
    intensity: string | null;
    duration_min: number | null;
    notes?: string | null;
    rpe?: number | null;
    tags?: string[];
    preset_id?: string | null;
    conditioning?: any;
  },
): Promise<void> {
  if (!AI_INTERNAL_TOKEN || !athleteId || !session?.date) return;
  try {
    const payload = {
      sessionId: session.id ?? `train-${session.date}-${Math.random().toString(36).slice(2, 8)}`,
      athleteId,
      date: session.date,
      createdAt: session.created_at ?? new Date().toISOString(),
      templateId: null,
      protocolFormat: null,
      machineType: session.conditioning?.modality ?? 'manual',
      machineProvider: 'manual',
      source: 'manual',
      sets: [],
      totalSets: 0,
      workSets: 0,
      restSets: 0,
      totalDurationSeconds: session.duration_min != null ? session.duration_min * 60 : null,
      totalCalories: null,
      totalWorkKj: null,
      avgWatts: null,
      peakWatts: null,
      avgHr: null,
      peakHr: null,
      sourceRecordIds: [],
      missingFields: ['per_set_detail'],
      // Non-HIIT additional fields — backend keeps them under the
      // session object for trend reasoning.
      kind: session.type,
      intensity: session.intensity,
      rpe: session.rpe ?? null,
      notes: session.notes ?? null,
      tags: Array.isArray(session.tags) ? session.tags : [],
      presetId: session.preset_id ?? null,
    };
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    await fetch(`${AI_INTERNAL_BASE}/ingest/session-log`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-internal-token': AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({ athleteId, session: payload }),
      signal: controller.signal,
    });
    clearTimeout(timer);
  } catch {
    /* fire-and-forget */
  }
}
