/**
 * Local-only zustand store for FS-021 Phase 1 manual lactate
 * entries. Routes every write through `validateManualLactateEntry`
 * so the spec's safety floor (clinical / causal / advice
 * language banned at the data layer) cannot be bypassed.
 *
 * Storage:
 *   - Local persistence via `secure-storage` only.
 *   - **No backend writes yet.** FS-021 spec § 1 keeps lactate
 *     phase-2 (CSV import, BLE devices) gated on Aaron approval.
 *     The store stays local until the worker writeback path is
 *     explicitly approved.
 *
 * UI:
 *   - **No UI route mounted yet.** This commit ships the store
 *     so a future approved UI batch can wire a form against it
 *     without re-deriving the contract.
 */

import { create } from 'zustand';
import {
  validateManualLactateEntry,
  type ManualLactateEntryInput,
} from '@lauburu/shared';
import { readStoredJson, writeStoredJson, removeStoredJson } from './secure-storage';

const STORAGE_KEY = 'fs021_lactate_entries_v1';
/**
 * Cap to keep the persisted blob small. Manual lactate entries
 * are typically a handful per user — 200 is plenty for years of
 * occasional testing without bloating storage.
 */
const ENTRIES_CAP = 200;

export interface LactateStoredEntry extends ManualLactateEntryInput {
  /** Stable id derived from dateTime + mmolPerL hash on insert. */
  id: string;
  /** Wall-clock ms when the entry was first stored. */
  createdAtMs: number;
}

export interface LactateStoreState {
  entries: LactateStoredEntry[];
  hydrated: boolean;
  error: string | null;
  warnings: string[];
  hydrate: () => Promise<void>;
  /**
   * Adds a single manual entry. Validates first; on rejection
   * stores `error` + does not mutate `entries`. On accept,
   * stores warnings (soft signals) so the UI can surface them
   * without blocking storage.
   */
  addEntry: (input: ManualLactateEntryInput) => Promise<{ ok: true; id: string } | { ok: false; reason: string }>;
  /** Removes a single entry by id. */
  removeEntry: (id: string) => Promise<void>;
  /** Clears all entries — useful for sign-out / reset. */
  clear: () => Promise<void>;
}

function makeId(input: ManualLactateEntryInput): string {
  // FNV-1a-ish 32-bit hash of dateTime + mmolPerL. Deterministic
  // for the same logical reading; collisions are tolerated
  // (caller can edit-then-resave, which produces a new id).
  const seed = `${input.dateTime}|${input.mmolPerL}`;
  let h = 0x811c9dc5;
  for (let i = 0; i < seed.length; i += 1) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return `lactate-${(h >>> 0).toString(16)}`;
}

async function persistSafely(entries: LactateStoredEntry[]): Promise<void> {
  try {
    if (entries.length === 0) {
      await removeStoredJson(STORAGE_KEY);
      return;
    }
    await writeStoredJson(STORAGE_KEY, { v: 1, entries });
  } catch {
    // Silent — local-first persistence should never block the UI.
  }
}

export const useLactateStore = create<LactateStoreState>((set, get) => ({
  entries: [],
  hydrated: false,
  error: null,
  warnings: [],

  hydrate: async () => {
    if (get().hydrated) return;
    const blob = await readStoredJson<{ v: number; entries: unknown }>(STORAGE_KEY);
    if (!blob || !Array.isArray(blob.entries)) {
      set({ hydrated: true });
      return;
    }
    // Re-validate every persisted entry on hydrate. If a future
    // schema tightening would reject an old row, drop it
    // silently rather than crash the app.
    const accepted: LactateStoredEntry[] = [];
    for (const raw of blob.entries) {
      if (!raw || typeof raw !== 'object') continue;
      const r = raw as Record<string, unknown>;
      const result = validateManualLactateEntry(r);
      if (!result.ok) continue;
      const id = typeof r.id === 'string' && r.id.length > 0 ? r.id : makeId(result.entry);
      const createdAtMs = typeof r.createdAtMs === 'number' && Number.isFinite(r.createdAtMs)
        ? r.createdAtMs
        : Date.now();
      accepted.push({ ...result.entry, id, createdAtMs });
    }
    set({ entries: accepted.slice(-ENTRIES_CAP), hydrated: true });
  },

  addEntry: async (input) => {
    const result = validateManualLactateEntry(input);
    if (!result.ok) {
      set({ error: result.reason, warnings: [] });
      return { ok: false, reason: result.reason };
    }
    const id = makeId(result.entry);
    const stored: LactateStoredEntry = { ...result.entry, id, createdAtMs: Date.now() };
    const next = [...get().entries.filter((e) => e.id !== id), stored].slice(-ENTRIES_CAP);
    set({ entries: next, error: null, warnings: result.warnings });
    void persistSafely(next);
    return { ok: true, id };
  },

  removeEntry: async (id) => {
    const next = get().entries.filter((e) => e.id !== id);
    set({ entries: next });
    void persistSafely(next);
  },

  clear: async () => {
    set({ entries: [], error: null, warnings: [] });
    await removeStoredJson(STORAGE_KEY);
  },
}));

/**
 * Test-only access: reset the store + storage. Lives behind a
 * function rather than the store API so production callers cannot
 * accidentally clear from a UI tap.
 */
export async function __test_resetLactateStore(): Promise<void> {
  await removeStoredJson(STORAGE_KEY);
  useLactateStore.setState({ entries: [], hydrated: false, error: null, warnings: [] });
}

/** Storage key exported for direct test inspection. */
export const __LACTATE_STORAGE_KEY = STORAGE_KEY;
