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

    clearAll: () => {
      set({ progress: {} });
      void persistSafely({});
    },
  }),
);

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
