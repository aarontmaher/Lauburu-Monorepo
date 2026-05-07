import { create } from 'zustand';
import { secureStorage } from './secure-storage';

export type TrainingIntent = 'push' | 'normal' | 'technique' | 'light' | 'rest';

export interface DailyJournalEntry {
  date: string;
  createdAt: string;
  updatedAt: string;
  sleepQuality: number;
  soreness: number;
  fatigue: number;
  stress: number;
  trainingIntent: TrainingIntent;
  injuryPainNotes: string;
  medicationSupplementNotes: string;
  notes: string;
}

export interface DailyJournalInput {
  date: string;
  sleepQuality: number;
  soreness: number;
  fatigue: number;
  stress: number;
  trainingIntent: TrainingIntent;
  injuryPainNotes?: string;
  medicationSupplementNotes?: string;
  notes?: string;
}

interface DailyJournalState {
  entries: DailyJournalEntry[];
  hydrated: boolean;
  hydrate: () => Promise<void>;
  upsertEntry: (input: DailyJournalInput) => DailyJournalEntry;
  getEntryForDate: (date: string) => DailyJournalEntry | undefined;
}

const STORAGE_KEY = 'daily_journal_store_v1';

function clampRating(value: number): number {
  if (!Number.isFinite(value)) return 3;
  return Math.max(1, Math.min(5, Math.round(value)));
}

function sanitizeIntent(value: unknown): TrainingIntent {
  if (value === 'push' || value === 'normal' || value === 'technique' || value === 'light' || value === 'rest') {
    return value;
  }
  return 'normal';
}

function sanitizeText(value: unknown): string {
  return typeof value === 'string' ? value.slice(0, 1200) : '';
}

function sanitizeEntries(raw: unknown): DailyJournalEntry[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item): DailyJournalEntry | null => {
      if (!item || typeof item !== 'object') return null;
      const value = item as Partial<DailyJournalEntry>;
      if (typeof value.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value.date)) return null;
      const now = new Date().toISOString();
      return {
        date: value.date,
        createdAt: typeof value.createdAt === 'string' ? value.createdAt : now,
        updatedAt: typeof value.updatedAt === 'string' ? value.updatedAt : now,
        sleepQuality: clampRating(value.sleepQuality ?? 3),
        soreness: clampRating(value.soreness ?? 3),
        fatigue: clampRating(value.fatigue ?? 3),
        stress: clampRating(value.stress ?? 3),
        trainingIntent: sanitizeIntent(value.trainingIntent),
        injuryPainNotes: sanitizeText(value.injuryPainNotes),
        medicationSupplementNotes: sanitizeText(value.medicationSupplementNotes),
        notes: sanitizeText(value.notes),
      };
    })
    .filter((item): item is DailyJournalEntry => item != null)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-90);
}

async function persistSafely(entries: DailyJournalEntry[]): Promise<void> {
  try {
    if (entries.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(-90)));
  } catch {
    // Local journal persistence should never block the check-in flow.
  }
}

export const useDailyJournalStore = create<DailyJournalState>((set, get) => ({
  entries: [],
  hydrated: false,

  hydrate: async () => {
    try {
      const raw = await secureStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      set({ entries: sanitizeEntries(parsed), hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },

  upsertEntry: (input) => {
    const now = new Date().toISOString();
    const existing = get().entries.find((entry) => entry.date === input.date);
    const entry: DailyJournalEntry = {
      date: input.date,
      createdAt: existing?.createdAt ?? now,
      updatedAt: now,
      sleepQuality: clampRating(input.sleepQuality),
      soreness: clampRating(input.soreness),
      fatigue: clampRating(input.fatigue),
      stress: clampRating(input.stress),
      trainingIntent: sanitizeIntent(input.trainingIntent),
      injuryPainNotes: sanitizeText(input.injuryPainNotes),
      medicationSupplementNotes: sanitizeText(input.medicationSupplementNotes),
      notes: sanitizeText(input.notes),
    };
    set((state) => {
      const entries = [
        ...state.entries.filter((item) => item.date !== input.date),
        entry,
      ].sort((a, b) => a.date.localeCompare(b.date)).slice(-90);
      void persistSafely(entries);
      return { entries };
    });
    return entry;
  },

  getEntryForDate: (date) => get().entries.find((entry) => entry.date === date),
}));
