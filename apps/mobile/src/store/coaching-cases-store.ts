/**
 * Coaching cases store — local-first MRU list of structured
 * "asked for a second opinion" cycles.
 *
 * Flow:
 *   1. User taps "Ask ChatGPT" on the Home coach card.
 *   2. App generates a prompt packet (buildCoachingPromptPacket) and
 *      opens the native share sheet.
 *   3. App saves a `pending` draft locally via `startPending()`.
 *   4. User returns to the app later; the Home banner reads the
 *      pending draft from `pending` and prompts for outcome capture.
 *   5. On capture, `completePending(usefulness, outcomeSummary?)`
 *      moves the draft into `cases` (MRU, capped at MAX_CASES) and
 *      clears `pending`.
 *
 * Persistence via secureStorage (Keychain/Keystore), same pattern as
 * nutrition-store. Two keys: `coaching_cases_v1` (full case list) and
 * `coaching_pending_v1` (single pending draft or null).
 *
 * This is the foundation for an eventual eval pipeline — the shape
 * of `CoachingCase` is the stable contract, future work can export
 * cases as JSONL for offline evals or dataset construction without
 * touching any UI.
 */
import { create } from 'zustand';
import type {
  CoachingCase,
  CoachingCaseDraft,
  CoachingCaseSource,
  CoachingCaseUsefulness,
  CoachingCaseContext,
  CoachingCaseExportLine,
} from '@lauburu/shared';
import { secureStorage } from './secure-storage';

const STORAGE_KEY_CASES = 'coaching_cases_v1';
const STORAGE_KEY_PENDING = 'coaching_pending_v1';

/** Cap the MRU list so the secureStorage entry stays bounded. */
const MAX_CASES = 50;

function genId(): string {
  return `cc-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function persistCasesSafely(cases: CoachingCase[]): Promise<void> {
  try {
    if (!cases || cases.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY_CASES);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY_CASES, JSON.stringify(cases));
  } catch {
    // Silent — see nutrition-store helper doc comment.
  }
}

async function persistPendingSafely(
  pending: CoachingCaseDraft | null,
): Promise<void> {
  try {
    if (!pending) {
      await secureStorage.removeItem(STORAGE_KEY_PENDING);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY_PENDING, JSON.stringify(pending));
  } catch {
    // Silent.
  }
}

interface CoachingCasesState {
  /** Completed cases, newest first, capped at MAX_CASES. */
  cases: CoachingCase[];
  /**
   * A case the user has started (shared a prompt packet) but not yet
   * completed (outcome not captured). At most one pending at a time —
   * starting a new one overwrites the previous, which keeps the UX
   * simple but may lose an uncaptured outcome. Acceptable trade-off
   * for a first slice.
   */
  pending: CoachingCaseDraft | null;
  /** True once the first hydrate attempt has completed. */
  hydrated: boolean;

  /** Load both keys from secureStorage. */
  hydrate: () => Promise<void>;

  /**
   * Start a new pending case. Called from the Home coach-card share
   * action right before the native share sheet opens. Overwrites any
   * previous pending draft.
   */
  startPending: (args: {
    context: CoachingCaseContext;
    prompt_packet: string;
    source: CoachingCaseSource;
  }) => void;

  /**
   * Complete the currently pending case with an outcome and move it
   * into the cases list. No-op if there is no pending draft.
   */
  completePending: (
    usefulness: CoachingCaseUsefulness,
    outcomeSummary?: string,
    followed?: boolean,
  ) => void;

  /** Discard the pending draft without completing it. */
  dismissPending: () => void;

  /** Wipe the entire case history and pending draft. */
  clearAll: () => void;

  /**
   * Serialize all completed cases into a JSONL array of
   * CoachingCaseExportLine. Future eval pipelines read this format
   * directly. Pure function — no side effects, no storage writes.
   */
  exportJsonlLines: () => CoachingCaseExportLine[];
}

export const useCoachingCasesStore = create<CoachingCasesState>((set, get) => ({
  cases: [],
  pending: null,
  hydrated: false,

  hydrate: async () => {
    try {
      const [rawCases, rawPending] = await Promise.all([
        secureStorage.getItem(STORAGE_KEY_CASES),
        secureStorage.getItem(STORAGE_KEY_PENDING),
      ]);

      let cases: CoachingCase[] = [];
      if (rawCases) {
        try {
          const parsed = JSON.parse(rawCases);
          if (Array.isArray(parsed)) {
            cases = parsed
              .filter(
                (c: any) =>
                  c &&
                  typeof c.id === 'string' &&
                  typeof c.prompt_packet === 'string',
              )
              .slice(0, MAX_CASES);
          }
        } catch {
          void secureStorage.removeItem(STORAGE_KEY_CASES);
        }
      }

      let pending: CoachingCaseDraft | null = null;
      if (rawPending) {
        try {
          const parsed = JSON.parse(rawPending);
          if (parsed && typeof parsed.id === 'string') {
            pending = parsed as CoachingCaseDraft;
          }
        } catch {
          void secureStorage.removeItem(STORAGE_KEY_PENDING);
        }
      }

      set({ cases, pending, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },

  startPending: ({ context, prompt_packet, source }) => {
    const draft: CoachingCaseDraft = {
      id: genId(),
      context,
      prompt_packet,
      source,
      shared_at: new Date().toISOString(),
    };
    set({ pending: draft });
    void persistPendingSafely(draft);
  },

  completePending: (usefulness, outcomeSummary, followed) => {
    const state = get();
    if (!state.pending) return;
    const completed: CoachingCase = {
      ...state.pending,
      completed_at: new Date().toISOString(),
      usefulness,
      outcome_summary: outcomeSummary?.trim() || undefined,
      followed,
    };
    const nextCases = [completed, ...state.cases].slice(0, MAX_CASES);
    set({ cases: nextCases, pending: null });
    void persistCasesSafely(nextCases);
    void persistPendingSafely(null);
  },

  dismissPending: () => {
    set({ pending: null });
    void persistPendingSafely(null);
  },

  clearAll: () => {
    set({ cases: [], pending: null });
    void persistCasesSafely([]);
    void persistPendingSafely(null);
  },

  exportJsonlLines: () => {
    return get().cases.map((c) => ({
      id: c.id,
      generated_at: c.context.generated_at,
      local_date: c.context.local_date,
      source: c.source,
      context: c.context,
      prompt_packet: c.prompt_packet,
      completed_at: c.completed_at,
      usefulness: c.usefulness,
      outcome_summary: c.outcome_summary,
      followed: c.followed,
    }));
  },
}));
