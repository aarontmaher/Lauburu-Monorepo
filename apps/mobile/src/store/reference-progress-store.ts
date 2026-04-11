/**
 * Reference progress store — local per-item training status for
 * mobile Reference techniques and transitions.
 *
 * Mirrors the web Reference's STATE.progress concept (tracked on
 * each node in the DOM tree) so that future cross-device sync can
 * translate mobile keys to web keys via a small key-format
 * adapter. For now the store is local-only and persisted to
 * secureStorage under the `reference_progress_v1` key.
 *
 * Status values:
 *   'none'     — not tracked (not stored; implicit default)
 *   'drilling' — actively drilling this move right now
 *   'learned'  — the user considers this landed in their game
 *   'tracking' — on a watch-list to come back to later
 *
 * Storage strategy:
 *   - Only non-'none' entries are persisted so the blob stays
 *     small as users move techniques between states.
 *   - Hydration is lenient: unknown keys or non-status values
 *     from a future / past schema are dropped silently.
 *   - Empty progress map removes the secureStorage entry entirely
 *     so clearAll leaves zero trace.
 *
 * Key format (mobile-stable):
 *   Technique rows:  `tech|<section>|<position>|<role>|<heading>|<label>`
 *   Transition rows: `tx|<sourceSection>|<sourcePosition>|<sourceRole>|<label>|<destination>`
 *   Transition keys are always rooted at the SOURCE side of the
 *   edge so the inbound "Coming in from" view on a destination
 *   shares the same key as the outbound "Transitions out" view on
 *   the source — marking a transition as learned from either side
 *   reflects identically on both surfaces.
 */
import { create } from 'zustand';
import { secureStorage } from './secure-storage';

const STORAGE_KEY = 'reference_progress_v1';

export type ProgressStatus = 'none' | 'drilling' | 'learned' | 'tracking';

/** Cycle order used by cycleProgress — tap a pill to advance. */
export const PROGRESS_CYCLE: readonly ProgressStatus[] = [
  'none',
  'drilling',
  'learned',
  'tracking',
] as const;

const VALID_STATUSES: ReadonlySet<ProgressStatus> = new Set(PROGRESS_CYCLE);

async function persistSafely(
  progress: Record<string, ProgressStatus>,
): Promise<void> {
  try {
    // Drop 'none' entries before persisting so the blob only carries
    // meaningful state. Store size stays bounded to the set of
    // items the user has actually interacted with.
    const filtered: Record<string, ProgressStatus> = {};
    for (const [k, v] of Object.entries(progress)) {
      if (v !== 'none') filtered[k] = v;
    }
    if (Object.keys(filtered).length === 0) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  } catch {
    // Silent — same pattern as other mobile stores.
  }
}

/**
 * Result of a progress import — counts of keys that were newly
 * added to the store, keys that overwrote existing entries
 * (status changed), and keys that were skipped (payload entry
 * had an unknown status value). The UI uses these counts to
 * surface a compact confirmation line after the import lands.
 */
export interface ProgressImportResult {
  added: number;
  updated: number;
  skipped: number;
}

interface ReferenceProgressState {
  progress: Record<string, ProgressStatus>;
  hydrated: boolean;

  hydrate: () => Promise<void>;

  /** Explicit set — used by future sync / import paths. */
  setProgress: (key: string, status: ProgressStatus) => void;

  /** Advance the given key through the PROGRESS_CYCLE by one step
   *  and return the new status. Primary UX entry point for pill
   *  taps in the Reference screen. */
  cycleProgress: (key: string) => ProgressStatus;

  /**
   * Import a batch of progress entries (keyed by the same format
   * the store itself uses). When `mode === 'merge'` the incoming
   * entries are added on top of existing state, overwriting any
   * matching keys. When `mode === 'replace'` existing state is
   * wiped first. Returns the per-key add/update/skip counts so
   * the UI can surface a confirmation line. Only 'drilling' /
   * 'learned' / 'tracking' values are accepted — 'none' and
   * unknown statuses are skipped.
   */
  importProgress: (
    entries: Record<string, string>,
    mode: 'merge' | 'replace',
  ) => ProgressImportResult;

  /** Wipe all per-item progress. */
  clearAll: () => void;
}

export const useReferenceProgressStore = create<ReferenceProgressState>(
  (set, get) => ({
    progress: {},
    hydrated: false,

    hydrate: async () => {
      try {
        const raw = await secureStorage.getItem(STORAGE_KEY);
        const progress: Record<string, ProgressStatus> = {};
        if (raw) {
          try {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === 'object') {
              for (const [k, v] of Object.entries(parsed)) {
                if (
                  typeof k === 'string' &&
                  typeof v === 'string' &&
                  VALID_STATUSES.has(v as ProgressStatus) &&
                  v !== 'none'
                ) {
                  progress[k] = v as ProgressStatus;
                }
              }
            }
          } catch {
            // Corrupted blob — drop it on the floor and start fresh
            // rather than propagating the parse error up.
            void secureStorage.removeItem(STORAGE_KEY);
          }
        }
        set({ progress, hydrated: true });
      } catch {
        set({ hydrated: true });
      }
    },

    setProgress: (key, status) => {
      let next: Record<string, ProgressStatus> = {};
      set((state) => {
        const copy = { ...state.progress };
        if (status === 'none') {
          delete copy[key];
        } else {
          copy[key] = status;
        }
        next = copy;
        return { progress: copy };
      });
      void persistSafely(next);
    },

    cycleProgress: (key) => {
      const current = get().progress[key] ?? 'none';
      const idx = PROGRESS_CYCLE.indexOf(current);
      const nextStatus =
        PROGRESS_CYCLE[(idx + 1) % PROGRESS_CYCLE.length] ?? 'none';
      get().setProgress(key, nextStatus);
      return nextStatus;
    },

    importProgress: (entries, mode) => {
      const result: ProgressImportResult = {
        added: 0,
        updated: 0,
        skipped: 0,
      };
      let next: Record<string, ProgressStatus> = {};
      set((state) => {
        const base: Record<string, ProgressStatus> =
          mode === 'replace' ? {} : { ...state.progress };
        for (const [rawKey, rawValue] of Object.entries(entries)) {
          if (typeof rawKey !== 'string' || !rawKey.trim()) {
            result.skipped++;
            continue;
          }
          if (
            typeof rawValue !== 'string' ||
            !VALID_STATUSES.has(rawValue as ProgressStatus) ||
            rawValue === 'none'
          ) {
            result.skipped++;
            continue;
          }
          const status = rawValue as ProgressStatus;
          const existing = state.progress[rawKey];
          if (existing == null) {
            result.added++;
          } else if (existing !== status) {
            result.updated++;
          } else {
            // Identical existing entry — merge mode keeps it,
            // replace mode is already rebuilding from empty so
            // it still counts as a fresh write. Track as added
            // under replace so the count is meaningful.
            if (mode === 'replace') result.added++;
          }
          base[rawKey] = status;
        }
        next = base;
        return { progress: base };
      });
      void persistSafely(next);
      return result;
    },

    clearAll: () => {
      set({ progress: {} });
      void persistSafely({});
    },
  }),
);

/**
 * Current schema version for the JSON export/import payload. The
 * parser refuses unknown versions so a future schema change has
 * a clean migration point instead of silently drifting.
 */
export const PROGRESS_EXPORT_VERSION = 1;

/** Shape of the JSON export payload. Intentionally small — just
 *  a version stamp, a capture timestamp, and the same key/status
 *  shape the store already uses at the top of its state. */
export interface ProgressExportPayload {
  version: number;
  exported_at: string;
  entries: Record<string, ProgressStatus>;
}

/**
 * Build a deterministic JSON export string for the user's current
 * progress. Includes only non-'none' entries (matches the
 * persist-safely contract elsewhere in this file). Stable key
 * ordering via Object.keys sort so the same inputs always yield
 * the same output string — useful for tests and for stable diffs
 * if the user pastes the same export twice.
 */
export function buildProgressExportJSON(
  progressMap: Record<string, ProgressStatus>,
): string {
  const entries: Record<string, ProgressStatus> = {};
  const keys = Object.keys(progressMap).sort();
  for (const k of keys) {
    const v = progressMap[k];
    if (v && v !== 'none') entries[k] = v;
  }
  const payload: ProgressExportPayload = {
    version: PROGRESS_EXPORT_VERSION,
    exported_at: new Date().toISOString(),
    entries,
  };
  return JSON.stringify(payload);
}

/**
 * Attempt to parse a pasted import payload. Accepts the full
 * text export (the JSON block is found by scanning for the first
 * `{"version"` occurrence), a bare JSON string, or even a
 * loosely-pasted block that contains extra whitespace at the
 * edges. Returns null on any parse failure so the UI can show
 * a clean "couldn't read that" error without crashing.
 */
export function parseProgressImportPayload(
  raw: string,
): ProgressExportPayload | null {
  if (typeof raw !== 'string') return null;
  let text = raw.trim();
  if (!text) return null;
  // If the user pasted the full text export (human + JSON),
  // strip everything before the first `{"version"` occurrence
  // so JSON.parse has a clean top-level object to chew on.
  const anchor = text.indexOf('{"version"');
  if (anchor > 0) text = text.slice(anchor);
  // Try a direct parse first.
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    // Second attempt — scan for the last `}` and try the
    // substring. Handles exports wrapped in extra text the
    // user forgot to delete.
    const lastBrace = text.lastIndexOf('}');
    if (lastBrace < 0) return null;
    try {
      parsed = JSON.parse(text.slice(0, lastBrace + 1));
    } catch {
      return null;
    }
  }
  if (!parsed || typeof parsed !== 'object') return null;
  const obj = parsed as Record<string, unknown>;
  if (typeof obj.version !== 'number') return null;
  if (obj.version !== PROGRESS_EXPORT_VERSION) return null;
  if (!obj.entries || typeof obj.entries !== 'object') return null;
  // Sanitize entries — keep only valid string-to-status pairs.
  const cleanEntries: Record<string, ProgressStatus> = {};
  for (const [k, v] of Object.entries(obj.entries as Record<string, unknown>)) {
    if (
      typeof k === 'string' &&
      k.length > 0 &&
      typeof v === 'string' &&
      VALID_STATUSES.has(v as ProgressStatus) &&
      v !== 'none'
    ) {
      cleanEntries[k] = v as ProgressStatus;
    }
  }
  return {
    version: PROGRESS_EXPORT_VERSION,
    exported_at:
      typeof obj.exported_at === 'string' ? obj.exported_at : '',
    entries: cleanEntries,
  };
}

/**
 * Build a stable progress key for a technique row. Deterministic
 * from the (section, position, role, heading, label) tuple so the
 * same technique always resolves to the same storage slot across
 * renders, role toggles, and app restarts.
 */
export function buildTechniqueProgressKey(
  section: string,
  position: string,
  role: string,
  heading: string,
  label: string,
): string {
  return `tech|${section}|${position}|${role}|${heading}|${label}`;
}

/**
 * Build a stable progress key for a transition edge. Always
 * rooted at the SOURCE side of the edge — the outbound
 * "Transitions out" row on Source/Role and the inbound
 * "Coming in from" row on Destination share the same key so
 * marking on one side reflects on the other.
 */
export function buildTransitionProgressKey(
  sourceSection: string,
  sourcePosition: string,
  sourceRole: string,
  label: string,
  destination: string,
): string {
  return `tx|${sourceSection}|${sourcePosition}|${sourceRole}|${label}|${destination}`;
}
