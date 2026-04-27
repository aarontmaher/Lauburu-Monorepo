/**
 * Reference progress store — local per-item training status,
 * notes, and timestamps for mobile Reference techniques and
 * transitions.
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
 * Per-key data tracked alongside status:
 *   - notes:      free-text annotation ("coach said start with
 *                 hip out", "drilled 3x with M today", etc.).
 *                 Empty string clears the note.
 *   - updated_at: ISO timestamp of the last mutation that touched
 *                 this key (status set OR note set). Drives the
 *                 Recent activity strip on the Reference screen.
 *
 * Storage strategy:
 *   - The persisted blob is now a versioned wrapper:
 *       { schema: 2, progress, notes, updated_at }
 *     with hydrate falling back to the legacy v1 raw progress
 *     map shape (`Record<string, ProgressStatus>` at the top
 *     level) so existing users keep their data on first launch.
 *   - Only non-'none' progress entries are persisted; notes and
 *     timestamps survive even when status is cleared so a user
 *     can keep a note about something they've stopped actively
 *     drilling without losing the context.
 *   - Empty wrapper (no progress, no notes) removes the
 *     secureStorage entry entirely so clearAll leaves zero trace.
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
const STORAGE_SCHEMA_VERSION = 2;

export type ProgressStatus = 'none' | 'drilling' | 'learned' | 'tracking';

/** Cycle order used by cycleProgress — tap a pill to advance. */
export const PROGRESS_CYCLE: readonly ProgressStatus[] = [
  'none',
  'drilling',
  'learned',
  'tracking',
] as const;

const VALID_STATUSES: ReadonlySet<ProgressStatus> = new Set(PROGRESS_CYCLE);

/**
 * Wrapped persistence shape (schema v2). Contains the three
 * parallel maps the store tracks:
 *   - progress:   non-'none' status entries only
 *   - notes:      non-empty free-text annotations
 *   - updated_at: ISO timestamps for any key in either map
 * On hydrate the parser also accepts the legacy v1 shape
 * (a flat `Record<string, ProgressStatus>` at the top level)
 * so existing users don't lose their progress on first launch
 * after the schema bump.
 */
interface PersistedProgressBlob {
  schema: number;
  progress: Record<string, ProgressStatus>;
  notes: Record<string, string>;
  updated_at: Record<string, string>;
}

async function persistSafely(
  progress: Record<string, ProgressStatus>,
  notes: Record<string, string>,
  updatedAt: Record<string, string>,
): Promise<void> {
  try {
    // Drop 'none' entries from progress and empty notes before
    // persisting so the blob only carries meaningful state.
    // Timestamps follow the same rule — only kept for keys that
    // still have status OR a non-empty note.
    const filteredProgress: Record<string, ProgressStatus> = {};
    for (const [k, v] of Object.entries(progress)) {
      if (v !== 'none') filteredProgress[k] = v;
    }
    const filteredNotes: Record<string, string> = {};
    for (const [k, v] of Object.entries(notes)) {
      if (typeof v === 'string' && v.length > 0) filteredNotes[k] = v;
    }
    const liveKeys = new Set([
      ...Object.keys(filteredProgress),
      ...Object.keys(filteredNotes),
    ]);
    const filteredUpdatedAt: Record<string, string> = {};
    for (const k of liveKeys) {
      const v = updatedAt[k];
      if (typeof v === 'string' && v.length > 0) filteredUpdatedAt[k] = v;
    }
    if (
      Object.keys(filteredProgress).length === 0 &&
      Object.keys(filteredNotes).length === 0
    ) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    const blob: PersistedProgressBlob = {
      schema: STORAGE_SCHEMA_VERSION,
      progress: filteredProgress,
      notes: filteredNotes,
      updated_at: filteredUpdatedAt,
    };
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(blob));
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
 *
 * `notesAdded` is reported separately so v2 imports can tell the
 * user "merged 12 statuses + 5 notes" without conflating the
 * two signals. Pre-v2 imports always report 0 here.
 */
export interface ProgressImportResult {
  added: number;
  updated: number;
  skipped: number;
  notesAdded: number;
}

interface ReferenceProgressState {
  progress: Record<string, ProgressStatus>;
  /** Free-text per-key annotations. Empty string deletes. */
  notes: Record<string, string>;
  /** ISO timestamps of the last mutation for each live key.
   *  Used by the Recent activity strip and by export schema v2. */
  updatedAt: Record<string, string>;
  hydrated: boolean;

  hydrate: () => Promise<void>;

  /** Explicit set — used by future sync / import paths. */
  setProgress: (key: string, status: ProgressStatus) => void;

  /** Advance the given key through the PROGRESS_CYCLE by one step
   *  and return the new status. Primary UX entry point for pill
   *  taps in the Reference screen. */
  cycleProgress: (key: string) => ProgressStatus;

  /** Set or clear the free-text note for a key. Empty string
   *  removes the note. Bumps `updatedAt` regardless. */
  setNote: (key: string, note: string) => void;

  /**
   * Import a batch of progress entries (keyed by the same format
   * the store itself uses). When `mode === 'merge'` the incoming
   * entries are added on top of existing state, overwriting any
   * matching keys. When `mode === 'replace'` existing state is
   * wiped first. Returns the per-key add/update/skip counts so
   * the UI can surface a confirmation line. Only 'drilling' /
   * 'learned' / 'tracking' values are accepted — 'none' and
   * unknown statuses are skipped. v2 payloads with `notes` and
   * `updated_at` maps merge those alongside the status entries.
   */
  importProgress: (
    payload: ProgressExportPayload,
    mode: 'merge' | 'replace',
  ) => ProgressImportResult;

  /** Wipe all per-item progress, notes, and timestamps. */
  clearAll: () => void;
}

export const useReferenceProgressStore = create<ReferenceProgressState>(
  (set, get) => ({
    progress: {},
    notes: {},
    updatedAt: {},
    hydrated: false,

    hydrate: async () => {
      try {
        const raw = await secureStorage.getItem(STORAGE_KEY);
        let progress: Record<string, ProgressStatus> = {};
        let notes: Record<string, string> = {};
        let updatedAt: Record<string, string> = {};
        if (raw) {
          try {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === 'object') {
              const obj = parsed as Record<string, unknown>;
              // Schema v2: wrapped blob with progress/notes/updated_at.
              // Detected by the explicit `schema` field — v1 blobs
              // never had a top-level `schema` key.
              if (typeof obj.schema === 'number' && obj.schema >= 2) {
                if (obj.progress && typeof obj.progress === 'object') {
                  for (const [k, v] of Object.entries(
                    obj.progress as Record<string, unknown>,
                  )) {
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
                if (obj.notes && typeof obj.notes === 'object') {
                  for (const [k, v] of Object.entries(
                    obj.notes as Record<string, unknown>,
                  )) {
                    if (typeof k === 'string' && typeof v === 'string' && v.length > 0) {
                      notes[k] = v;
                    }
                  }
                }
                if (obj.updated_at && typeof obj.updated_at === 'object') {
                  for (const [k, v] of Object.entries(
                    obj.updated_at as Record<string, unknown>,
                  )) {
                    if (typeof k === 'string' && typeof v === 'string' && v.length > 0) {
                      updatedAt[k] = v;
                    }
                  }
                }
              } else {
                // Legacy v1: top-level is the raw progress map
                // (`Record<string, ProgressStatus>`). Migrate in
                // place — notes/updatedAt start empty for these
                // users, which is correct (they had no notes
                // before this schema bump).
                for (const [k, v] of Object.entries(obj)) {
                  if (
                    typeof k === 'string' &&
                    typeof v === 'string' &&
                    VALID_STATUSES.has(v as ProgressStatus) &&
                    v !== 'none'
                  ) {
                    progress[k] = v as ProgressStatus;
                  }
                }
                // Persist immediately in the v2 wrapper shape so
                // the legacy blob is retired on first launch.
                void persistSafely(progress, notes, updatedAt);
              }
            }
          } catch {
            // Corrupted blob — drop it on the floor and start fresh
            // rather than propagating the parse error up.
            void secureStorage.removeItem(STORAGE_KEY);
            progress = {};
            notes = {};
            updatedAt = {};
          }
        }
        set({ progress, notes, updatedAt, hydrated: true });
      } catch {
        set({ hydrated: true });
      }
    },

    setProgress: (key, status) => {
      let nextProgress: Record<string, ProgressStatus> = {};
      let nextNotes: Record<string, string> = {};
      let nextUpdatedAt: Record<string, string> = {};
      set((state) => {
        const progress = { ...state.progress };
        const notes = { ...state.notes };
        const updatedAt = { ...state.updatedAt };
        if (status === 'none') {
          delete progress[key];
          // Status cleared but the user might still want their
          // note. Only drop the timestamp when there's also no
          // note left for this key.
          if (!notes[key]) delete updatedAt[key];
        } else {
          progress[key] = status;
          updatedAt[key] = new Date().toISOString();
        }
        nextProgress = progress;
        nextNotes = notes;
        nextUpdatedAt = updatedAt;
        return { progress, notes, updatedAt };
      });
      void persistSafely(nextProgress, nextNotes, nextUpdatedAt);
    },

    cycleProgress: (key) => {
      const current = get().progress[key] ?? 'none';
      const idx = PROGRESS_CYCLE.indexOf(current);
      const nextStatus =
        PROGRESS_CYCLE[(idx + 1) % PROGRESS_CYCLE.length] ?? 'none';
      get().setProgress(key, nextStatus);
      return nextStatus;
    },

    setNote: (key, note) => {
      let nextProgress: Record<string, ProgressStatus> = {};
      let nextNotes: Record<string, string> = {};
      let nextUpdatedAt: Record<string, string> = {};
      set((state) => {
        const progress = state.progress;
        const notes = { ...state.notes };
        const updatedAt = { ...state.updatedAt };
        const trimmed = typeof note === 'string' ? note : '';
        if (trimmed.length === 0) {
          delete notes[key];
          // Note cleared — drop the timestamp only when status
          // is also gone (no live data left for this key).
          if (progress[key] == null) {
            delete updatedAt[key];
          } else {
            updatedAt[key] = new Date().toISOString();
          }
        } else {
          notes[key] = trimmed;
          updatedAt[key] = new Date().toISOString();
        }
        nextProgress = progress;
        nextNotes = notes;
        nextUpdatedAt = updatedAt;
        return { notes, updatedAt };
      });
      void persistSafely(nextProgress, nextNotes, nextUpdatedAt);
    },

    importProgress: (payload, mode) => {
      const result: ProgressImportResult = {
        added: 0,
        updated: 0,
        skipped: 0,
        notesAdded: 0,
      };
      let nextProgress: Record<string, ProgressStatus> = {};
      let nextNotes: Record<string, string> = {};
      let nextUpdatedAt: Record<string, string> = {};
      set((state) => {
        const progress: Record<string, ProgressStatus> =
          mode === 'replace' ? {} : { ...state.progress };
        const notes: Record<string, string> =
          mode === 'replace' ? {} : { ...state.notes };
        const updatedAt: Record<string, string> =
          mode === 'replace' ? {} : { ...state.updatedAt };

        // Status entries first.
        for (const [rawKey, rawValue] of Object.entries(payload.entries)) {
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
          if (mode === 'replace') {
            result.added++;
          } else if (existing == null) {
            result.added++;
          } else if (existing !== status) {
            result.updated++;
          }
          progress[rawKey] = status;
          // Prefer the payload's timestamp when present, fall
          // back to import time so the entry doesn't sit at the
          // epoch in the Recent activity strip.
          const payloadTs = payload.updated_at?.[rawKey];
          updatedAt[rawKey] =
            typeof payloadTs === 'string' && payloadTs.length > 0
              ? payloadTs
              : new Date().toISOString();
        }

        // Notes — only present in v2 payloads. Skipped silently
        // when missing.
        if (payload.notes) {
          for (const [rawKey, rawValue] of Object.entries(payload.notes)) {
            if (typeof rawKey !== 'string' || !rawKey.trim()) continue;
            if (typeof rawValue !== 'string' || rawValue.length === 0) continue;
            notes[rawKey] = rawValue;
            result.notesAdded++;
            // Make sure the note's key has a timestamp even if it
            // had no status entry in the payload.
            if (!updatedAt[rawKey]) {
              const payloadTs = payload.updated_at?.[rawKey];
              updatedAt[rawKey] =
                typeof payloadTs === 'string' && payloadTs.length > 0
                  ? payloadTs
                  : new Date().toISOString();
            }
          }
        }

        nextProgress = progress;
        nextNotes = notes;
        nextUpdatedAt = updatedAt;
        return { progress, notes, updatedAt };
      });
      void persistSafely(nextProgress, nextNotes, nextUpdatedAt);
      return result;
    },

    clearAll: () => {
      set({ progress: {}, notes: {}, updatedAt: {} });
      void persistSafely({}, {}, {});
    },
  }),
);

/**
 * Current schema version for the JSON export/import payload. The
 * parser accepts the current version AND the previous one (v1)
 * so a v1 export pasted onto a v2-aware build still imports
 * cleanly — it just lacks notes and timestamps.
 */
export const PROGRESS_EXPORT_VERSION = 2;
const PROGRESS_EXPORT_LEGACY_VERSIONS: ReadonlySet<number> = new Set([1]);

/** Shape of the JSON export payload. v2 adds optional `notes`
 *  and `updated_at` parallel maps alongside the existing
 *  `entries` (status) map. v1 payloads parse to the same shape
 *  with both new fields left undefined so the consumer doesn't
 *  branch on version. */
export interface ProgressExportPayload {
  version: number;
  exported_at: string;
  entries: Record<string, ProgressStatus>;
  notes?: Record<string, string>;
  updated_at?: Record<string, string>;
}

/**
 * Build a deterministic JSON export string for the user's current
 * progress. Includes only non-'none' status entries and only
 * non-empty notes. Stable key ordering via Object.keys sort so
 * the same inputs always yield the same output string — useful
 * for tests and for stable diffs if the user pastes the same
 * export twice.
 */
export function buildProgressExportJSON(
  progressMap: Record<string, ProgressStatus>,
  notesMap: Record<string, string> = {},
  updatedAtMap: Record<string, string> = {},
): string {
  const entries: Record<string, ProgressStatus> = {};
  const sortedProgressKeys = Object.keys(progressMap).sort();
  for (const k of sortedProgressKeys) {
    const v = progressMap[k];
    if (v && v !== 'none') entries[k] = v;
  }
  const notes: Record<string, string> = {};
  const sortedNoteKeys = Object.keys(notesMap).sort();
  for (const k of sortedNoteKeys) {
    const v = notesMap[k];
    if (typeof v === 'string' && v.length > 0) notes[k] = v;
  }
  // Only emit updated_at for keys that ended up in entries OR
  // notes — orphan timestamps would just bloat the payload.
  const liveKeys = new Set([
    ...Object.keys(entries),
    ...Object.keys(notes),
  ]);
  const updated_at: Record<string, string> = {};
  for (const k of Array.from(liveKeys).sort()) {
    const v = updatedAtMap[k];
    if (typeof v === 'string' && v.length > 0) updated_at[k] = v;
  }
  const payload: ProgressExportPayload = {
    version: PROGRESS_EXPORT_VERSION,
    exported_at: new Date().toISOString(),
    entries,
    notes,
    updated_at,
  };
  return JSON.stringify(payload);
}

/**
 * Attempt to parse a pasted import payload. Accepts the full
 * text export (the JSON block is found by scanning for the first
 * `{"version"` occurrence), a bare JSON string, or even a
 * loosely-pasted block that contains extra whitespace at the
 * edges. Returns null on any parse failure so the UI can show
 * a clean "couldn't read that" error without crashing. Both v1
 * and v2 payloads parse to the same `ProgressExportPayload`
 * shape; v1 payloads have `notes` and `updated_at` undefined.
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
  // Accept the current version OR any explicitly-supported
  // legacy version. Future bumps add their predecessors here.
  if (
    obj.version !== PROGRESS_EXPORT_VERSION &&
    !PROGRESS_EXPORT_LEGACY_VERSIONS.has(obj.version)
  ) {
    return null;
  }
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
  // Sanitize notes (v2 only — v1 has no notes field).
  let cleanNotes: Record<string, string> | undefined;
  if (obj.notes && typeof obj.notes === 'object') {
    cleanNotes = {};
    for (const [k, v] of Object.entries(obj.notes as Record<string, unknown>)) {
      if (typeof k === 'string' && k.length > 0 && typeof v === 'string' && v.length > 0) {
        cleanNotes[k] = v;
      }
    }
  }
  // Sanitize updated_at (v2 only).
  let cleanUpdatedAt: Record<string, string> | undefined;
  if (obj.updated_at && typeof obj.updated_at === 'object') {
    cleanUpdatedAt = {};
    for (const [k, v] of Object.entries(
      obj.updated_at as Record<string, unknown>,
    )) {
      if (typeof k === 'string' && k.length > 0 && typeof v === 'string' && v.length > 0) {
        cleanUpdatedAt[k] = v;
      }
    }
  }
  return {
    version: obj.version,
    exported_at:
      typeof obj.exported_at === 'string' ? obj.exported_at : '',
    entries: cleanEntries,
    notes: cleanNotes,
    updated_at: cleanUpdatedAt,
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

/**
 * Parsed-key descriptor — the structured tuple recovered from a
 * stored progress key. Returned by `parseProgressKey` so the
 * Recent activity strip and any other "list of keys" surface can
 * render readable position + role + label info without having
 * to hand-roll string splits at the call site.
 */
export type ParsedProgressKey =
  | {
      kind: 'tech';
      section: string;
      position: string;
      role: string;
      heading: string;
      label: string;
    }
  | {
      kind: 'tx';
      sourceSection: string;
      sourcePosition: string;
      sourceRole: string;
      label: string;
      destination: string;
    }
  | null;

/**
 * Parse a stored progress key back into its structured tuple.
 * Returns null on any malformed key — callers should treat null
 * as "stale or unknown key, skip rendering" rather than crashing.
 *
 * The split is tolerant of position / heading / technique labels
 * containing the `|` character only if those labels were never
 * built by `buildTechniqueProgressKey` (which doesn't escape, so
 * the canonical mobile-seed names — none of which contain pipes
 * — round-trip cleanly). For tech keys we expect exactly 6 parts
 * after the `tech` tag; for transition keys exactly 5 parts after
 * the `tx` tag.
 */
export function parseProgressKey(key: string): ParsedProgressKey {
  if (typeof key !== 'string' || key.length === 0) return null;
  const parts = key.split('|');
  const kind = parts[0];
  if (kind === 'tech') {
    if (parts.length !== 6) return null;
    return {
      kind: 'tech',
      section: parts[1] ?? '',
      position: parts[2] ?? '',
      role: parts[3] ?? '',
      heading: parts[4] ?? '',
      label: parts[5] ?? '',
    };
  }
  if (kind === 'tx') {
    if (parts.length !== 6) return null;
    return {
      kind: 'tx',
      sourceSection: parts[1] ?? '',
      sourcePosition: parts[2] ?? '',
      sourceRole: parts[3] ?? '',
      label: parts[4] ?? '',
      destination: parts[5] ?? '',
    };
  }
  return null;
}
