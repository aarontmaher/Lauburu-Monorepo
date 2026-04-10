/**
 * Machine store — live and last-session cardio machine metrics.
 *
 * This is a thin Zustand wrapper over the `machine-connector` service.
 * Today the connector is a stub so the store's connectionState stays
 * 'disconnected' and the sample cache is empty. The UI can still write
 * manual-entry metrics into `lastSessionMetrics` directly — the store
 * is provenance-aware (WorkoutSource), so manual + live coexist cleanly.
 *
 * WHY THIS IS SEPARATE FROM THE TRAINING STORE
 *
 * Training-store holds the persisted TrainingSession list (manual
 * logging, edits, deletes). Machine-store holds ephemeral live
 * metrics during a session and the most recent machine snapshot so
 * the entry form can prefill numbers and the SessionCard can show
 * machine detail. The handoff is explicit: when a session is logged,
 * the entry form copies machine-store.lastSessionMetrics into the
 * TrainingSession's ConditioningDetail.machine_metrics field. After
 * that, training-store is the source of truth.
 */
import { create } from 'zustand';
import type { MachineMetrics, WorkoutSource } from '@lauburu/shared';
import {
  getMachineConnector,
  type LiveMachineSample,
  type MachineConnectionState,
} from '../services/machine-connector';

interface MachineState {
  /** Current connector state. 'disconnected' while the stub is in place. */
  connectionState: MachineConnectionState;
  /** Most recent live sample from a connected machine. Null if none. */
  latestSample: LiveMachineSample | null;
  /**
   * Cached machine metrics for the current or most recently logged
   * session. Used to prefill the Train entry form and to render the
   * SessionCard detail when the session was machine-sourced.
   */
  lastSessionMetrics: MachineMetrics | null;
  /** Provenance flag for lastSessionMetrics. */
  lastSessionSource: WorkoutSource | null;

  setLastSessionMetrics: (
    metrics: MachineMetrics | null,
    source: WorkoutSource,
  ) => void;
  clearLastSession: () => void;
  refreshConnectionState: () => void;
}

export const useMachineStore = create<MachineState>((set) => ({
  connectionState: 'disconnected',
  latestSample: null,
  lastSessionMetrics: null,
  lastSessionSource: null,

  setLastSessionMetrics: (metrics, source) =>
    set({ lastSessionMetrics: metrics, lastSessionSource: source }),

  clearLastSession: () =>
    set({ lastSessionMetrics: null, lastSessionSource: null }),

  /**
   * Re-query the connector service for its state. Safe to call from
   * component mount. Today this always returns 'disconnected'.
   */
  refreshConnectionState: () => {
    const connector = getMachineConnector();
    set({
      connectionState: connector.getState(),
      latestSample: connector.getLatestSample(),
    });
  },
}));
