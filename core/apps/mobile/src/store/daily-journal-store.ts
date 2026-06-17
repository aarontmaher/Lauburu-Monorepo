import { create } from 'zustand';
import { secureStorage } from './secure-storage';

export type TrainingIntent = 'push' | 'normal' | 'technique' | 'light' | 'rest';
export type CustomJournalAction =
  | 'start'
  | 'stop'
  | 'dose_change'
  | 'break_start'
  | 'break_end'
  | 'one_off'
  | 'symptom_note'
  | 'custom_note';

export type CustomJournalCategory =
  | 'supplement'
  | 'medication'
  | 'nutrition'
  | 'recovery'
  | 'training'
  | 'sleep'
  | 'symptom'
  | 'other';

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

export interface CustomJournalItem {
  id: string;
  name: string;
  category: CustomJournalCategory;
  customCategory: string;
  dose: string;
  unit: string;
  frequencyTiming: string;
  startDate: string;
  stopDate: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export interface CustomJournalItemInput {
  name: string;
  category: CustomJournalCategory;
  customCategory?: string;
  dose?: string;
  unit?: string;
  frequencyTiming?: string;
  startDate: string;
  stopDate?: string;
  notes?: string;
}

export interface CustomJournalEvent {
  id: string;
  itemId: string | null;
  itemName: string;
  action: CustomJournalAction;
  date: string;
  dose: string;
  unit: string;
  notes: string;
  createdAt: string;
}

export interface CustomJournalEventInput {
  itemId?: string | null;
  itemName?: string;
  action: CustomJournalAction;
  date: string;
  dose?: string;
  unit?: string;
  notes?: string;
}

interface DailyJournalState {
  entries: DailyJournalEntry[];
  customItems: CustomJournalItem[];
  customEvents: CustomJournalEvent[];
  hydrated: boolean;
  hydrate: () => Promise<void>;
  upsertEntry: (input: DailyJournalInput) => DailyJournalEntry;
  addCustomItem: (input: CustomJournalItemInput) => CustomJournalItem;
  addJournalEvent: (input: CustomJournalEventInput) => CustomJournalEvent;
  stopCustomItem: (id: string, date: string, notes?: string) => CustomJournalEvent | null;
  getEntryForDate: (date: string) => DailyJournalEntry | undefined;
  getActiveCustomItems: (onDate?: string) => CustomJournalItem[];
  getStoppedCustomItems: () => CustomJournalItem[];
  getRecentJournalEvents: (limit?: number) => CustomJournalEvent[];
}

const STORAGE_KEY = 'daily_journal_store_v1';

interface PersistedJournalBlob {
  entries: DailyJournalEntry[];
  customItems: CustomJournalItem[];
  customEvents: CustomJournalEvent[];
}

function genId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

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

function sanitizeCategory(value: unknown): CustomJournalCategory {
  if (
    value === 'supplement' ||
    value === 'medication' ||
    value === 'nutrition' ||
    value === 'recovery' ||
    value === 'training' ||
    value === 'sleep' ||
    value === 'symptom' ||
    value === 'other'
  ) {
    return value;
  }
  return 'other';
}

function sanitizeAction(value: unknown): CustomJournalAction {
  if (
    value === 'start' ||
    value === 'stop' ||
    value === 'dose_change' ||
    value === 'break_start' ||
    value === 'break_end' ||
    value === 'one_off' ||
    value === 'symptom_note' ||
    value === 'custom_note'
  ) {
    return value;
  }
  return 'custom_note';
}

function sanitizeDate(value: unknown, fallback = new Date().toISOString().slice(0, 10)): string {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : fallback;
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

function sanitizeItems(raw: unknown): CustomJournalItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item): CustomJournalItem | null => {
      if (!item || typeof item !== 'object') return null;
      const value = item as Partial<CustomJournalItem>;
      const name = sanitizeText(value.name).trim();
      if (!name) return null;
      const now = new Date().toISOString();
      return {
        id: sanitizeText(value.id) || genId('ji'),
        name,
        category: sanitizeCategory(value.category),
        customCategory: sanitizeText(value.customCategory),
        dose: sanitizeText(value.dose),
        unit: sanitizeText(value.unit),
        frequencyTiming: sanitizeText(value.frequencyTiming),
        startDate: sanitizeDate(value.startDate),
        stopDate: value.stopDate ? sanitizeDate(value.stopDate, '') : '',
        notes: sanitizeText(value.notes),
        createdAt: typeof value.createdAt === 'string' ? value.createdAt : now,
        updatedAt: typeof value.updatedAt === 'string' ? value.updatedAt : now,
      };
    })
    .filter((item): item is CustomJournalItem => item != null)
    .sort((a, b) => a.startDate.localeCompare(b.startDate))
    .slice(-120);
}

function sanitizeEvents(raw: unknown): CustomJournalEvent[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item): CustomJournalEvent | null => {
      if (!item || typeof item !== 'object') return null;
      const value = item as Partial<CustomJournalEvent>;
      const itemName = sanitizeText(value.itemName).trim();
      const notes = sanitizeText(value.notes);
      if (!itemName && !notes) return null;
      const now = new Date().toISOString();
      return {
        id: sanitizeText(value.id) || genId('je'),
        itemId: typeof value.itemId === 'string' && value.itemId ? value.itemId : null,
        itemName: itemName || 'Journal note',
        action: sanitizeAction(value.action),
        date: sanitizeDate(value.date),
        dose: sanitizeText(value.dose),
        unit: sanitizeText(value.unit),
        notes,
        createdAt: typeof value.createdAt === 'string' ? value.createdAt : now,
      };
    })
    .filter((item): item is CustomJournalEvent => item != null)
    .sort((a, b) => a.date.localeCompare(b.date) || a.createdAt.localeCompare(b.createdAt))
    .slice(-240);
}

function sanitizeBlob(raw: unknown): PersistedJournalBlob {
  if (Array.isArray(raw)) {
    return { entries: sanitizeEntries(raw), customItems: [], customEvents: [] };
  }
  if (!raw || typeof raw !== 'object') {
    return { entries: [], customItems: [], customEvents: [] };
  }
  const value = raw as Partial<PersistedJournalBlob>;
  return {
    entries: sanitizeEntries(value.entries),
    customItems: sanitizeItems(value.customItems),
    customEvents: sanitizeEvents(value.customEvents),
  };
}

async function persistSafely(blob: PersistedJournalBlob): Promise<void> {
  try {
    if (blob.entries.length === 0 && blob.customItems.length === 0 && blob.customEvents.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify({
      entries: blob.entries.slice(-90),
      customItems: blob.customItems.slice(-120),
      customEvents: blob.customEvents.slice(-240),
    }));
  } catch {
    // Local journal persistence should never block the check-in flow.
  }
}

export const useDailyJournalStore = create<DailyJournalState>((set, get) => ({
  entries: [],
  customItems: [],
  customEvents: [],
  hydrated: false,

  hydrate: async () => {
    try {
      const raw = await secureStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      const blob = sanitizeBlob(parsed);
      set({ ...blob, hydrated: true });
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
      void persistSafely({
        entries,
        customItems: state.customItems,
        customEvents: state.customEvents,
      });
      return { entries };
    });
    return entry;
  },

  addCustomItem: (input) => {
    const now = new Date().toISOString();
    const item: CustomJournalItem = {
      id: genId('ji'),
      name: sanitizeText(input.name).trim(),
      category: sanitizeCategory(input.category),
      customCategory: sanitizeText(input.customCategory),
      dose: sanitizeText(input.dose),
      unit: sanitizeText(input.unit),
      frequencyTiming: sanitizeText(input.frequencyTiming),
      startDate: sanitizeDate(input.startDate),
      stopDate: input.stopDate ? sanitizeDate(input.stopDate, '') : '',
      notes: sanitizeText(input.notes),
      createdAt: now,
      updatedAt: now,
    };
    set((state) => {
      const customItems = [...state.customItems, item]
        .sort((a, b) => a.startDate.localeCompare(b.startDate))
        .slice(-120);
      const startEvent: CustomJournalEvent = {
        id: genId('je'),
        itemId: item.id,
        itemName: item.name,
        action: item.stopDate ? 'one_off' : 'start',
        date: item.startDate,
        dose: item.dose,
        unit: item.unit,
        notes: item.notes,
        createdAt: now,
      };
      const customEvents = [...state.customEvents, startEvent]
        .sort((a, b) => a.date.localeCompare(b.date) || a.createdAt.localeCompare(b.createdAt))
        .slice(-240);
      void persistSafely({ entries: state.entries, customItems, customEvents });
      return { customItems, customEvents };
    });
    return item;
  },

  addJournalEvent: (input) => {
    const item = input.itemId
      ? get().customItems.find((candidate) => candidate.id === input.itemId)
      : null;
    const now = new Date().toISOString();
    const event: CustomJournalEvent = {
      id: genId('je'),
      itemId: item?.id ?? input.itemId ?? null,
      itemName: (item?.name ?? sanitizeText(input.itemName).trim()) || 'Journal note',
      action: sanitizeAction(input.action),
      date: sanitizeDate(input.date),
      dose: sanitizeText(input.dose),
      unit: sanitizeText(input.unit),
      notes: sanitizeText(input.notes),
      createdAt: now,
    };
    set((state) => {
      let customItems = state.customItems;
      if (event.itemId && (event.action === 'stop' || event.action === 'break_start')) {
        customItems = state.customItems.map((candidate) =>
          candidate.id === event.itemId
            ? { ...candidate, stopDate: event.date, updatedAt: now }
            : candidate,
        );
      }
      if (event.itemId && event.action === 'break_end') {
        customItems = state.customItems.map((candidate) =>
          candidate.id === event.itemId
            ? { ...candidate, stopDate: '', updatedAt: now }
            : candidate,
        );
      }
      const customEvents = [...state.customEvents, event]
        .sort((a, b) => a.date.localeCompare(b.date) || a.createdAt.localeCompare(b.createdAt))
        .slice(-240);
      void persistSafely({ entries: state.entries, customItems, customEvents });
      return { customItems, customEvents };
    });
    return event;
  },

  stopCustomItem: (id, date, notes) => {
    const item = get().customItems.find((candidate) => candidate.id === id);
    if (!item) return null;
    return get().addJournalEvent({
      itemId: id,
      action: 'stop',
      date,
      notes,
    });
  },

  getEntryForDate: (date) => get().entries.find((entry) => entry.date === date),
  getActiveCustomItems: (onDate = new Date().toISOString().slice(0, 10)) =>
    get().customItems.filter((item) => item.startDate <= onDate && (!item.stopDate || item.stopDate > onDate)),
  getStoppedCustomItems: () => get().customItems.filter((item) => !!item.stopDate),
  getRecentJournalEvents: (limit = 8) => [...get().customEvents].sort((a, b) => b.date.localeCompare(a.date) || b.createdAt.localeCompare(a.createdAt)).slice(0, limit),
}));
