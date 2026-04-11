/**
 * HIIT saved protocols store — local MRU library of named HIIT
 * protocols the user can recall with a single tap from the Train
 * HIIT flow.
 *
 * Mirrors the barcode-favorites pattern inside nutrition-store:
 * secureStorage-backed, MRU ordering by `last_used_at`, dedupe by
 * normalized label, capped at MAX_PROTOCOLS so the keychain stays
 * bounded. Auto-saves on every HIIT session that carries a
 * user-provided label at log time — no separate "Save" button —
 * so frequently-used protocols naturally rise to the top.
 *
 * Complementary to (not a replacement for) the existing
 * "↺ Repeat last HIIT" button shipped in commit 00dc975 — that
 * button reuses the most recent logged session's protocol,
 * whereas this store holds a NAMED library of protocols that
 * persists across sessions and can be recalled in any order.
 */
import { create } from 'zustand';
import type { MachineMetrics, Modality } from '@lauburu/shared';
import { secureStorage } from './secure-storage';

const STORAGE_KEY = 'hiit_protocols_v1';

/** Cap the library so the keychain entry stays bounded. */
const MAX_PROTOCOLS = 12;

/**
 * Compact progression snapshot carried on a saved protocol — the
 * last-session machine metrics and duration worth remembering when
 * the user recalls this protocol. Only fields that were actually
 * present at log time are populated; missing fields are omitted
 * rather than zero-filled so the UI can tell the difference
 * between "no data" and "recorded zero".
 *
 * Intentionally narrower than MachineMetrics — we keep only the
 * few fields that make sense as "target to beat" numbers. This
 * keeps the secureStorage entry small and the UI line readable.
 */
export interface SavedHIITProtocolMetrics {
  /** Total distance in metres, if the machine console showed it. */
  distance_m?: number;
  /** Total calories (kcal), if the machine console showed it. */
  calories?: number;
  /** Total work output (kJ), rower-biased fallback alongside calories. */
  kilojoules?: number;
  /** Average power across the session (W), if present. */
  avg_power_w?: number;
  /** Average HR across the session (bpm), if present. */
  avg_hr_bpm?: number;
  /** Session duration in minutes — always present even without a machine. */
  duration_min?: number;
  /** ISO timestamp of the session this snapshot came from. */
  captured_at: string;
}

/**
 * Saved HIIT protocol — a named recipe for a recurring interval
 * session. Label is user-provided and mandatory (the store only
 * auto-saves when the user has explicitly named a protocol).
 */
export interface SavedHIITProtocol {
  id: string;
  /** User-provided name, e.g. "Friday bike smoker". Required. */
  label: string;
  work_s: number;
  rest_s: number;
  rounds: number;
  /** Modality the protocol was last run on, if any. */
  modality?: Modality;
  /** ISO timestamp of the most recent save/use. MRU ordering. */
  last_used_at: string;
  /** How many times the protocol has been saved/used. */
  use_count: number;
  /**
   * Last-session progression snapshot. Preserved across no-metrics
   * saves so the "last: 5.2km · 185W" target line keeps showing
   * even after a session logged without machine numbers. Only
   * overwritten when a newer snapshot carries at least one
   * meaningful numeric field.
   */
  last_metrics?: SavedHIITProtocolMetrics;
}

function genId(): string {
  return `hp-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

/** Normalize labels for dedupe — case-insensitive, trimmed. */
function normalizeLabel(label: string): string {
  return label.trim().toLowerCase();
}

async function persistSafely(protocols: SavedHIITProtocol[]): Promise<void> {
  try {
    if (!protocols || protocols.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(protocols));
  } catch {
    // Silent — same pattern as nutrition-store persist helpers.
  }
}

interface HIITProtocolsState {
  protocols: SavedHIITProtocol[];
  hydrated: boolean;

  hydrate: () => Promise<void>;

  /**
   * Save a protocol. If a protocol with the same normalized label
   * already exists, it's replaced (bumping last_used_at to now and
   * incrementing use_count). Called automatically from the Train
   * HIIT log path when a session with a label is logged.
   *
   * `metrics` is optional and partial — pass whatever the session
   * actually captured. If at least one meaningful field is present
   * the snapshot is stored; otherwise any existing snapshot on the
   * matching protocol is preserved (so a no-metrics session doesn't
   * wipe a previously-captured target).
   *
   * `duration_min` is passed separately because it's always known
   * (from the session's duration), even when no machine metrics
   * were entered.
   */
  saveProtocol: (args: {
    label: string;
    work_s: number;
    rest_s: number;
    rounds: number;
    modality?: Modality;
    metrics?: Partial<MachineMetrics>;
    duration_min?: number;
  }) => void;

  /** Remove a protocol by id. Called from long-press on a pill. */
  removeProtocol: (id: string) => void;

  /** Wipe the full library. */
  clearAll: () => void;
}

/**
 * Pure helper: compute a single compact "progression vs last" string
 * for a freshly-logged session versus a prior saved-protocol snapshot.
 *
 * Design goals:
 * - Only ever return ONE delta — the highest-priority field for which
 *   both the current and prior session have a value. Multiple deltas
 *   in one banner is noise.
 * - Never invent precision. A delta is only computed when BOTH values
 *   are present on the same field.
 * - Rounded-zero deltas render as "matched last" so users get explicit
 *   positive feedback for repeating exactly.
 * - Returns null when there is nothing meaningful to say (no prior
 *   snapshot, no comparable fields) — the UI should then render the
 *   existing success banner alone.
 *
 * Field priority (first match wins):
 *   distance_m → avg_power_w → calories → kilojoules → avg_hr_bpm → duration_min
 *
 * HR deltas intentionally show as raw "+3bpm vs last" without valence
 * coloring — higher HR is not automatically "better" (could indicate
 * under-recovery) and we don't have the context to judge here.
 */
export function buildProgressionDelta(
  current: {
    metrics?: Partial<MachineMetrics>;
    duration_min?: number;
  },
  prior: SavedHIITProtocolMetrics | undefined,
): string | null {
  if (!prior) return null;

  const m = current.metrics ?? {};

  /**
   * Format a signed number with an explicit sign. `+123`, `-5`, `0`.
   * Always passes through Math.round so the output never shows fake
   * fractional precision.
   */
  const signed = (n: number): string => {
    const r = Math.round(n);
    if (r > 0) return `+${r}`;
    return `${r}`;
  };

  // Ordered list of picks to try. First one with both values wins.
  const picks: Array<{
    cur: number;
    old: number;
    format: (delta: number) => string;
  }> = [];

  if (m.distance_m != null && prior.distance_m != null) {
    picks.push({
      cur: m.distance_m,
      old: prior.distance_m,
      format: (d) => {
        const abs = Math.abs(d);
        // Switch to km when the delta or prior total lives in km range
        // — keeps the banner compact for real cardio distances.
        if (abs >= 1000 || prior.distance_m! >= 1000) {
          const km = d / 1000;
          const sign = km > 0 ? '+' : km < 0 ? '' : '';
          return `${sign}${km.toFixed(1)}km vs last`;
        }
        return `${signed(d)}m vs last`;
      },
    });
  }
  if (m.avg_power_w != null && prior.avg_power_w != null) {
    picks.push({
      cur: m.avg_power_w,
      old: prior.avg_power_w,
      format: (d) => `${signed(d)}W vs last`,
    });
  }
  if (m.calories != null && prior.calories != null) {
    picks.push({
      cur: m.calories,
      old: prior.calories,
      format: (d) => `${signed(d)}kcal vs last`,
    });
  }
  if (m.kilojoules != null && prior.kilojoules != null) {
    picks.push({
      cur: m.kilojoules,
      old: prior.kilojoules,
      format: (d) => `${signed(d)}kJ vs last`,
    });
  }
  if (m.avg_hr_bpm != null && prior.avg_hr_bpm != null) {
    picks.push({
      cur: m.avg_hr_bpm,
      old: prior.avg_hr_bpm,
      format: (d) => `${signed(d)}bpm avg vs last`,
    });
  }
  if (current.duration_min != null && prior.duration_min != null) {
    picks.push({
      cur: current.duration_min,
      old: prior.duration_min,
      format: (d) => `${signed(d)}min vs last`,
    });
  }

  if (picks.length === 0) return null;

  const best = picks[0];
  const delta = best.cur - best.old;

  // Rounded-zero comparison — anything that rounds to 0 on the chosen
  // field is "matched", not a fake "+0W" delta. For distance we use a
  // slightly wider tolerance (±1m rounds to 0 anyway, but allow ±2m).
  if (Math.round(delta) === 0) return 'matched last';

  return best.format(delta);
}

export const useHIITProtocolsStore = create<HIITProtocolsState>((set, get) => ({
  protocols: [],
  hydrated: false,

  hydrate: async () => {
    try {
      const raw = await secureStorage.getItem(STORAGE_KEY);
      let protocols: SavedHIITProtocol[] = [];
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed)) {
            protocols = parsed
              .filter(
                (p: any) =>
                  p &&
                  typeof p.id === 'string' &&
                  typeof p.label === 'string' &&
                  p.label.trim().length > 0,
              )
              .slice(0, MAX_PROTOCOLS);
            // Ensure MRU order in case saved shape drifts.
            protocols.sort((a, b) =>
              b.last_used_at.localeCompare(a.last_used_at),
            );
          }
        } catch {
          void secureStorage.removeItem(STORAGE_KEY);
        }
      }
      set({ protocols, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },

  saveProtocol: ({
    label,
    work_s,
    rest_s,
    rounds,
    modality,
    metrics,
    duration_min,
  }) => {
    const trimmed = label.trim();
    if (!trimmed) return;
    let nextProtocols: SavedHIITProtocol[] = [];
    set((state) => {
      const now = new Date().toISOString();
      const norm = normalizeLabel(trimmed);
      // Dedupe by normalized label — find existing match and remove it
      // so the fresh entry replaces it at the front.
      const existing = state.protocols.find(
        (p) => normalizeLabel(p.label) === norm,
      );
      const filtered = state.protocols.filter(
        (p) => normalizeLabel(p.label) !== norm,
      );

      // Build the new progression snapshot from whatever numeric fields
      // the caller actually passed. `duration_min` is kept separately
      // because every session has a duration even without a machine,
      // but it alone is not enough to qualify as "meaningful metrics" —
      // a session with only a duration would otherwise wipe a
      // previously-captured output snapshot.
      const mm = metrics ?? {};
      const hasOutputField =
        mm.distance_m != null ||
        mm.calories != null ||
        mm.kilojoules != null ||
        mm.avg_power_w != null ||
        mm.avg_hr_bpm != null;

      let nextLastMetrics: SavedHIITProtocolMetrics | undefined =
        existing?.last_metrics;
      if (hasOutputField) {
        nextLastMetrics = {
          distance_m: mm.distance_m,
          calories: mm.calories,
          kilojoules: mm.kilojoules,
          avg_power_w: mm.avg_power_w,
          avg_hr_bpm: mm.avg_hr_bpm,
          duration_min: duration_min,
          captured_at: now,
        };
      } else if (duration_min != null && existing?.last_metrics == null) {
        // Duration-only fallback ONLY when there's no prior snapshot
        // to preserve. This gives freshly-created protocols something
        // minimal to display ("last: 18 min") before any machine data
        // ever lands.
        nextLastMetrics = {
          duration_min,
          captured_at: now,
        };
      }

      const fresh: SavedHIITProtocol = {
        id: existing?.id ?? genId(),
        label: trimmed,
        work_s,
        rest_s,
        rounds,
        modality,
        last_used_at: now,
        use_count: (existing?.use_count ?? 0) + 1,
        last_metrics: nextLastMetrics,
      };
      nextProtocols = [fresh, ...filtered].slice(0, MAX_PROTOCOLS);
      return { protocols: nextProtocols };
    });
    void persistSafely(nextProtocols);
  },

  removeProtocol: (id) => {
    let nextProtocols: SavedHIITProtocol[] = [];
    set((state) => {
      nextProtocols = state.protocols.filter((p) => p.id !== id);
      return { protocols: nextProtocols };
    });
    void persistSafely(nextProtocols);
  },

  clearAll: () => {
    set({ protocols: [] });
    void persistSafely([]);
  },
}));
