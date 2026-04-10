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
import type { Modality } from '@lauburu/shared';
import { secureStorage } from './secure-storage';

const STORAGE_KEY = 'hiit_protocols_v1';

/** Cap the library so the keychain entry stays bounded. */
const MAX_PROTOCOLS = 12;

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
   */
  saveProtocol: (args: {
    label: string;
    work_s: number;
    rest_s: number;
    rounds: number;
    modality?: Modality;
  }) => void;

  /** Remove a protocol by id. Called from long-press on a pill. */
  removeProtocol: (id: string) => void;

  /** Wipe the full library. */
  clearAll: () => void;
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

  saveProtocol: ({ label, work_s, rest_s, rounds, modality }) => {
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
      const fresh: SavedHIITProtocol = {
        id: existing?.id ?? genId(),
        label: trimmed,
        work_s,
        rest_s,
        rounds,
        modality,
        last_used_at: now,
        use_count: (existing?.use_count ?? 0) + 1,
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
