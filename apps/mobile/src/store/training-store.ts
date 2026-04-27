/**
 * Training session store — manages manually logged grappling sessions.
 * Sessions are stored locally and trigger health pipeline recomputation.
 */
import { create } from 'zustand';
import type { TrainingSession, TrainingSessionInput } from '@lauburu/shared';
import {
  readStoredJson,
  writeStoredJson,
  removeStoredJson,
} from './secure-storage';

const STORAGE_KEY = 'training_sessions_v1';

async function persistSafely(sessions: TrainingSession[]): Promise<void> {
  if (sessions.length === 0) {
    await removeStoredJson(STORAGE_KEY);
    return;
  }
  await writeStoredJson(STORAGE_KEY, sessions);
}

function sanitizeSessions(value: unknown): TrainingSession[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (session): session is TrainingSession =>
      !!session &&
      typeof session === 'object' &&
      typeof (session as TrainingSession).id === 'string' &&
      typeof (session as TrainingSession).date === 'string' &&
      typeof (session as TrainingSession).type === 'string' &&
      typeof (session as TrainingSession).intensity === 'string' &&
      typeof (session as TrainingSession).duration_min === 'number',
  );
}

function refreshFeedbackExample(date: string): void {
  // Lazy require avoids a top-level circular import with feedback-store,
  // which already reads training-store state during assembly.
  setTimeout(() => {
    try {
      const { useFeedbackStore } = require('./feedback-store') as typeof import('./feedback-store');
      useFeedbackStore.getState().assembleForDate(date);
    } catch {
      // Silent — training persistence must not depend on feedback assembly.
    }
  }, 0);
}

interface TrainingState {
  sessions: TrainingSession[];
  hydrated: boolean;

  hydrate: () => Promise<void>;

  addSession: (input: TrainingSessionInput) => TrainingSession;
  editSession: (id: string, input: Partial<TrainingSessionInput>) => void;
  removeSession: (id: string) => void;
  getSessionsForRange: (startDate: string, endDate: string) => TrainingSession[];
}

function generateId(): string {
  return `ts-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useTrainingStore = create<TrainingState>((set, get) => ({
  sessions: [],
  hydrated: false,

  hydrate: async () => {
    const parsed = await readStoredJson<unknown>(STORAGE_KEY);
    set({ sessions: sanitizeSessions(parsed), hydrated: true });
  },

  addSession: (input) => {
    // Auto-merge live BLE session-ring stats into the conditioning
    // detail when present. Previously only the HIIT save path read
    // from getSessionStats() — a generic "Save training session"
    // (zone-2 bike ride, conditioning finisher) would discard the
    // live HR/watts/cadence/distance/kcal that the ring had just
    // captured. Now any non-HIIT session save merges live metrics
    // into input.conditioning.machine_metrics + flips the source
    // label to 'machine_connected' when anything was captured.
    let liveAugmentedConditioning = input.conditioning;
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const ble = require('../services/ble-connect');
      if (typeof ble?.getSessionStats === 'function') {
        const stats = ble.getSessionStats();
        if (stats && typeof stats === 'object' && stats.sampleCount > 0) {
          const existing: any = input.conditioning ?? { subtype: 'steady_state' as any };
          const existingMm: any = existing.machine_metrics ?? {};
          const merged = {
            ...existingMm,
            avg_hr_bpm: existingMm.avg_hr_bpm ?? (typeof stats.avgHrBpm === 'number' ? stats.avgHrBpm : undefined),
            peak_hr_bpm: existingMm.peak_hr_bpm ?? (typeof stats.peakHrBpm === 'number' ? stats.peakHrBpm : undefined),
            avg_power_w: existingMm.avg_power_w ?? (typeof stats.avgPowerW === 'number' ? stats.avgPowerW : undefined),
            peak_power_w: existingMm.peak_power_w ?? (typeof stats.peakPowerW === 'number' ? stats.peakPowerW : undefined),
            avg_cadence: existingMm.avg_cadence ?? (typeof stats.avgCadenceRpm === 'number' ? stats.avgCadenceRpm : undefined),
            distance_m: existingMm.distance_m ?? (typeof stats.totalDistanceM === 'number' && stats.totalDistanceM > 0 ? stats.totalDistanceM : undefined),
            calories: existingMm.calories ?? (typeof stats.totalEnergyKcal === 'number' && stats.totalEnergyKcal > 0 ? stats.totalEnergyKcal : undefined),
            kilojoules: existingMm.kilojoules ?? (typeof stats.totalEnergyKj === 'number' && stats.totalEnergyKj > 0 ? stats.totalEnergyKj : undefined),
          };
          // Drop undefined fields so we don't pollute the record shape.
          const cleanedMm: any = {};
          for (const k of Object.keys(merged)) if (merged[k] != null) cleanedMm[k] = merged[k];
          if (Object.keys(cleanedMm).length > 0) {
            liveAugmentedConditioning = {
              ...existing,
              source: existing.source ?? 'machine_connected',
              machine_metrics: cleanedMm,
            } as any;
            if (typeof ble.clearSession === 'function') {
              try { ble.clearSession(); } catch { /* ignore */ }
            }
          }
        }
      }
    } catch { /* non-fatal — save still works without BLE merge */ }

    const session: TrainingSession = {
      id: generateId(),
      created_at: new Date().toISOString(),
      date: input.date,
      type: input.type,
      intensity: input.intensity,
      duration_min: input.duration_min,
      rounds: input.rounds,
      rpe: input.rpe,
      tags: input.tags ?? [],
      notes: input.notes ?? '',
      conditioning: liveAugmentedConditioning,
      segments: input.segments,
      preset_id: input.preset_id,
      persisted: false,
    };
    set((state) => {
      const sessions = [...state.sessions, session];
      void persistSafely(sessions);
      return { sessions };
    });
    refreshFeedbackExample(session.date);
    // Durable backend ingest for non-HIIT sessions (HIIT sessions use
    // their own /ingest/session-log path via hiit-workout-store; those
    // mirror here via preset_id='hiit:<id>' and we skip to avoid
    // double-counting). Fire-and-forget.
    try {
      const isMirroredHiit = typeof session.preset_id === 'string' && session.preset_id.startsWith('hiit:');
      if (!isMirroredHiit) {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const authMod = require('./auth-store');
        const uid = authMod?.useAuthStore?.getState?.()?.user?.id;
        if (uid) {
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          const sync = require('../services/ai-hiit-sync');
          if (typeof sync?.syncTrainingSessionToAiBackend === 'function') {
            void sync.syncTrainingSessionToAiBackend(uid, session).catch(() => {});
          }
        }
      }
    } catch { /* non-fatal */ }
    return session;
  },

  editSession: (id, input) => {
    const previous = get().sessions.find((s) => s.id === id);
    let updatedDate: string | null = null;
    set((state) => {
      const sessions = state.sessions.map((s) => {
        if (s.id !== id) return s;
        const updated = {
          ...s,
          ...input,
          tags: input.tags ?? s.tags,
          notes: input.notes ?? s.notes,
        };
        updatedDate = updated.date;
        return updated;
      });
      void persistSafely(sessions);
      return { sessions };
    });
    if (previous?.date) refreshFeedbackExample(previous.date);
    if (updatedDate && updatedDate !== previous?.date) {
      refreshFeedbackExample(updatedDate);
    }
  },

  removeSession: (id) => {
    const previous = get().sessions.find((s) => s.id === id);
    set((state) => {
      const sessions = state.sessions.filter((s) => s.id !== id);
      void persistSafely(sessions);
      return { sessions };
    });
    if (previous?.date) refreshFeedbackExample(previous.date);
  },

  getSessionsForRange: (startDate, endDate) => {
    return get().sessions.filter(
      (s) => s.date >= startDate && s.date <= endDate,
    );
  },
}));
