import { create } from 'zustand';
import { supabase } from './supabase';
import { secureStorage } from './secure-storage';
import { useAuthStore } from './auth-store';

export type JournalItemCategory =
  | 'medication'
  | 'peptide'
  | 'supplement'
  | 'nasal_spray'
  | 'inhaler'
  | 'sleep_aid'
  | 'caffeine'
  | 'nutrition_change'
  | 'training_change'
  | 'injury'
  | 'pain'
  | 'illness'
  | 'respiratory_treatment'
  | 'weight_cut_intervention'
  | 'surgery'
  | 'custom';

export type JournalEventType =
  | 'start'
  | 'stop'
  | 'dose_change'
  | 'break_start'
  | 'break_end'
  | 'one_off_use'
  | 'symptom_note'
  | 'training_note'
  | 'injury_note'
  | 'custom';

export type JournalConfidence =
  | 'user_reported'
  | 'prescription_verified'
  | 'device_verified'
  | 'imported_uncertain';

export interface CustomJournalItem {
  id: string;
  userId: string | null;
  category: JournalItemCategory;
  name: string;
  unit: string | null;
  defaultDose: number | null;
  defaultFrequency: string | null;
  mayAffectMetrics: boolean;
  notes: string | null;
  source: 'user' | 'imported_apple_notes' | 'imported_csv';
  confidence: JournalConfidence;
  createdAt: string;
  updatedAt: string;
  pendingSync: boolean;
}

export interface CustomJournalEvent {
  id: string;
  userId: string | null;
  itemId: string;
  eventType: JournalEventType;
  effectiveAt: string;
  dose: number | null;
  unit: string | null;
  frequency: string | null;
  notes: string | null;
  source: 'user' | 'imported_apple_notes';
  confidence: JournalConfidence;
  createdAt: string;
  pendingSync: boolean;
}

export interface CreateJournalItemInput {
  category: JournalItemCategory;
  name: string;
  unit?: string | null;
  defaultDose?: number | null;
  defaultFrequency?: string | null;
  mayAffectMetrics?: boolean;
  notes?: string | null;
  startDate: string;
}

export interface AddJournalEventInput {
  itemId: string;
  eventType: JournalEventType;
  effectiveAt: string;
  dose?: number | null;
  unit?: string | null;
  frequency?: string | null;
  notes?: string | null;
}

type SyncStatus = 'idle' | 'syncing' | 'synced' | 'failed';

interface CustomJournalState {
  items: CustomJournalItem[];
  events: CustomJournalEvent[];
  hydrated: boolean;
  syncStatus: SyncStatus;
  lastSyncAt: string | null;
  lastSyncError: string | null;
  hydrate: () => Promise<void>;
  syncFromSupabase: () => Promise<boolean>;
  syncPendingToSupabase: () => Promise<boolean>;
  createItem: (input: CreateJournalItemInput) => Promise<CustomJournalItem | null>;
  addEvent: (input: AddJournalEventInput) => Promise<CustomJournalEvent | null>;
  getActiveItems: (onDate?: string) => CustomJournalItem[];
  getRecentEvents: (limit?: number) => CustomJournalEvent[];
  countActiveMetricAffectingItems: (onDate?: string) => number;
}

interface PersistedCustomJournalBlob {
  items: CustomJournalItem[];
  events: CustomJournalEvent[];
  lastSyncAt: string | null;
  lastSyncError: string | null;
}

const STORAGE_KEY = 'custom_journal_store_v1';

export const JOURNAL_CATEGORY_LABELS: Record<JournalItemCategory, string> = {
  medication: 'Medication',
  peptide: 'Peptide',
  supplement: 'Supplement',
  nasal_spray: 'Nasal spray',
  inhaler: 'Inhaler',
  sleep_aid: 'Sleep aid',
  caffeine: 'Caffeine',
  nutrition_change: 'Nutrition change',
  training_change: 'Training change',
  injury: 'Injury',
  pain: 'Pain',
  illness: 'Illness',
  respiratory_treatment: 'Respiratory treatment',
  weight_cut_intervention: 'Weight-cut intervention',
  surgery: 'Surgery',
  custom: 'Custom',
};

export const JOURNAL_EVENT_LABELS: Record<JournalEventType, string> = {
  start: 'Start',
  stop: 'Stop',
  dose_change: 'Dose changed',
  break_start: 'Break',
  break_end: 'Resume',
  one_off_use: 'One-off',
  symptom_note: 'Symptom note',
  training_note: 'Training note',
  injury_note: 'Injury note',
  custom: 'Note',
};

export const BEGINNER_JOURNAL_CATEGORIES: JournalItemCategory[] = [
  'medication',
  'peptide',
  'supplement',
  'nasal_spray',
  'inhaler',
  'sleep_aid',
  'caffeine',
  'nutrition_change',
  'training_change',
  'injury',
  'pain',
  'illness',
  'respiratory_treatment',
  'weight_cut_intervention',
  'surgery',
  'custom',
];

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function toEffectiveAt(date: string): string {
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : todayIsoDate();
  return `${normalized}T00:00:00.000Z`;
}

function dateFromEffectiveAt(value: string): string {
  return value.slice(0, 10);
}

function genId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function sanitizeText(value: unknown, maxLength = 1200): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim().slice(0, maxLength);
  return trimmed.length > 0 ? trimmed : null;
}

function sanitizeNumber(value: unknown): number | null {
  if (value == null || value === '') return null;
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function sanitizeCategory(value: unknown): JournalItemCategory {
  return BEGINNER_JOURNAL_CATEGORIES.includes(value as JournalItemCategory)
    ? value as JournalItemCategory
    : 'custom';
}

function sanitizeEventType(value: unknown): JournalEventType {
  if (
    value === 'start' ||
    value === 'stop' ||
    value === 'dose_change' ||
    value === 'break_start' ||
    value === 'break_end' ||
    value === 'one_off_use' ||
    value === 'symptom_note' ||
    value === 'training_note' ||
    value === 'injury_note' ||
    value === 'custom'
  ) {
    return value;
  }
  return 'custom';
}

function sanitizeConfidence(value: unknown): JournalConfidence {
  if (
    value === 'user_reported' ||
    value === 'prescription_verified' ||
    value === 'device_verified' ||
    value === 'imported_uncertain'
  ) {
    return value;
  }
  return 'user_reported';
}

function buildPersistedBlob(state: Pick<CustomJournalState, 'items' | 'events' | 'lastSyncAt' | 'lastSyncError'>): PersistedCustomJournalBlob {
  return {
    items: state.items.slice(-120),
    events: state.events.slice(-240),
    lastSyncAt: state.lastSyncAt,
    lastSyncError: state.lastSyncError,
  };
}

function sanitizeBlob(raw: unknown): PersistedCustomJournalBlob {
  if (!raw || typeof raw !== 'object') {
    return { items: [], events: [], lastSyncAt: null, lastSyncError: null };
  }
  const value = raw as Partial<PersistedCustomJournalBlob>;
  const items = Array.isArray(value.items) ? value.items.map(sanitizeItem).filter((item): item is CustomJournalItem => item != null) : [];
  const events = Array.isArray(value.events) ? value.events.map(sanitizeEvent).filter((event): event is CustomJournalEvent => event != null) : [];
  return {
    items,
    events,
    lastSyncAt: typeof value.lastSyncAt === 'string' ? value.lastSyncAt : null,
    lastSyncError: typeof value.lastSyncError === 'string' ? value.lastSyncError : null,
  };
}

function sanitizeItem(value: unknown): CustomJournalItem | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Partial<CustomJournalItem>;
  const name = sanitizeText(item.name, 160);
  if (!name) return null;
  const now = new Date().toISOString();
  return {
    id: typeof item.id === 'string' && item.id ? item.id : genId('ji'),
    userId: typeof item.userId === 'string' ? item.userId : null,
    category: sanitizeCategory(item.category),
    name,
    unit: sanitizeText(item.unit, 40),
    defaultDose: sanitizeNumber(item.defaultDose),
    defaultFrequency: sanitizeText(item.defaultFrequency, 160),
    mayAffectMetrics: item.mayAffectMetrics !== false,
    notes: sanitizeText(item.notes),
    source: item.source === 'imported_apple_notes' || item.source === 'imported_csv' ? item.source : 'user',
    confidence: sanitizeConfidence(item.confidence),
    createdAt: typeof item.createdAt === 'string' ? item.createdAt : now,
    updatedAt: typeof item.updatedAt === 'string' ? item.updatedAt : now,
    pendingSync: item.pendingSync === true,
  };
}

function sanitizeEvent(value: unknown): CustomJournalEvent | null {
  if (!value || typeof value !== 'object') return null;
  const event = value as Partial<CustomJournalEvent>;
  if (typeof event.itemId !== 'string' || !event.itemId) return null;
  const now = new Date().toISOString();
  return {
    id: typeof event.id === 'string' && event.id ? event.id : genId('je'),
    userId: typeof event.userId === 'string' ? event.userId : null,
    itemId: event.itemId,
    eventType: sanitizeEventType(event.eventType),
    effectiveAt: typeof event.effectiveAt === 'string' ? event.effectiveAt : toEffectiveAt(todayIsoDate()),
    dose: sanitizeNumber(event.dose),
    unit: sanitizeText(event.unit, 40),
    frequency: sanitizeText(event.frequency, 160),
    notes: sanitizeText(event.notes),
    source: event.source === 'imported_apple_notes' ? 'imported_apple_notes' : 'user',
    confidence: sanitizeConfidence(event.confidence),
    createdAt: typeof event.createdAt === 'string' ? event.createdAt : now,
    pendingSync: event.pendingSync === true,
  };
}

async function persistSafely(blob: PersistedCustomJournalBlob): Promise<void> {
  try {
    if (blob.items.length === 0 && blob.events.length === 0 && !blob.lastSyncAt && !blob.lastSyncError) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(blob));
  } catch {
    // Local custom journal persistence must not block the app.
  }
}

function itemToRow(item: CustomJournalItem, userId: string) {
  return {
    id: item.id,
    user_id: userId,
    category: item.category,
    name: item.name,
    unit: item.unit,
    default_dose: item.defaultDose,
    default_frequency: item.defaultFrequency,
    may_affect_metrics: item.mayAffectMetrics,
    notes: item.notes,
    source: item.source,
    confidence: item.confidence,
    created_at: item.createdAt,
    updated_at: item.updatedAt,
  };
}

function eventToRow(event: CustomJournalEvent, userId: string) {
  return {
    id: event.id,
    user_id: userId,
    item_id: event.itemId,
    event_type: event.eventType,
    effective_at: event.effectiveAt,
    dose: event.dose,
    unit: event.unit,
    frequency: event.frequency,
    notes: event.notes,
    source: event.source,
    confidence: event.confidence,
    created_at: event.createdAt,
  };
}

function rowToItem(row: any): CustomJournalItem {
  return {
    id: row.id,
    userId: row.user_id,
    category: sanitizeCategory(row.category),
    name: row.name,
    unit: row.unit ?? null,
    defaultDose: row.default_dose == null ? null : Number(row.default_dose),
    defaultFrequency: row.default_frequency ?? null,
    mayAffectMetrics: row.may_affect_metrics !== false,
    notes: row.notes ?? null,
    source: row.source === 'imported_apple_notes' || row.source === 'imported_csv' ? row.source : 'user',
    confidence: sanitizeConfidence(row.confidence),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    pendingSync: false,
  };
}

function rowToEvent(row: any): CustomJournalEvent {
  return {
    id: row.id,
    userId: row.user_id,
    itemId: row.item_id,
    eventType: sanitizeEventType(row.event_type),
    effectiveAt: row.effective_at,
    dose: row.dose == null ? null : Number(row.dose),
    unit: row.unit ?? null,
    frequency: row.frequency ?? null,
    notes: row.notes ?? null,
    source: row.source === 'imported_apple_notes' ? 'imported_apple_notes' : 'user',
    confidence: sanitizeConfidence(row.confidence),
    createdAt: row.created_at,
    pendingSync: false,
  };
}

function isItemActive(item: CustomJournalItem, events: CustomJournalEvent[], onDate: string): boolean {
  const dateEvents = events
    .filter((event) => event.itemId === item.id && dateFromEffectiveAt(event.effectiveAt) <= onDate)
    .sort((a, b) => a.effectiveAt.localeCompare(b.effectiveAt) || a.createdAt.localeCompare(b.createdAt));
  if (dateEvents.length === 0) return false;
  const latest = dateEvents[dateEvents.length - 1];
  return latest.eventType === 'start' || latest.eventType === 'dose_change' || latest.eventType === 'break_end';
}

export const useCustomJournalStore = create<CustomJournalState>((set, get) => ({
  items: [],
  events: [],
  hydrated: false,
  syncStatus: 'idle',
  lastSyncAt: null,
  lastSyncError: null,

  hydrate: async () => {
    try {
      const raw = await secureStorage.getItem(STORAGE_KEY);
      const blob = sanitizeBlob(raw ? JSON.parse(raw) : null);
      set({ ...blob, hydrated: true, syncStatus: 'idle' });
    } catch {
      set({ hydrated: true, syncStatus: 'idle' });
    }
  },

  syncFromSupabase: async () => {
    const userId = useAuthStore.getState().user?.id ?? null;
    if (!userId) return false;
    set({ syncStatus: 'syncing', lastSyncError: null });
    try {
      const [itemsResult, eventsResult] = await Promise.all([
        supabase.from('journal_items').select('*').order('updated_at', { ascending: false }).limit(120),
        supabase.from('journal_events').select('*').order('effective_at', { ascending: false }).limit(240),
      ]);
      if (itemsResult.error) throw itemsResult.error;
      if (eventsResult.error) throw eventsResult.error;
      const next = {
        items: (itemsResult.data ?? []).map(rowToItem),
        events: (eventsResult.data ?? []).map(rowToEvent),
        lastSyncAt: new Date().toISOString(),
        lastSyncError: null,
      };
      set({ ...next, syncStatus: 'synced' });
      void persistSafely(next);
      return true;
    } catch (error: any) {
      const message = error?.message ?? 'Custom journal sync failed';
      set({ syncStatus: 'failed', lastSyncError: message });
      return false;
    }
  },

  syncPendingToSupabase: async () => {
    const userId = useAuthStore.getState().user?.id ?? null;
    if (!userId) return false;
    const pendingItems = get().items.filter((item) => item.pendingSync);
    const pendingEvents = get().events.filter((event) => event.pendingSync);
    if (pendingItems.length === 0 && pendingEvents.length === 0) return true;
    set({ syncStatus: 'syncing', lastSyncError: null });
    try {
      if (pendingItems.length > 0) {
        const { error } = await supabase.from('journal_items').upsert(pendingItems.map((item) => itemToRow(item, userId)));
        if (error) throw error;
      }
      if (pendingEvents.length > 0) {
        const { error } = await supabase.from('journal_events').upsert(pendingEvents.map((event) => eventToRow(event, userId)));
        if (error) throw error;
      }
      set((state) => {
        const next = {
          items: state.items.map((item) => ({ ...item, userId, pendingSync: false })),
          events: state.events.map((event) => ({ ...event, userId, pendingSync: false })),
          lastSyncAt: new Date().toISOString(),
          lastSyncError: null,
        };
        void persistSafely(next);
        return { ...next, syncStatus: 'synced' };
      });
      return true;
    } catch (error: any) {
      const message = error?.message ?? 'Custom journal upload failed';
      set({ syncStatus: 'failed', lastSyncError: message });
      return false;
    }
  },

  createItem: async (input) => {
    const name = sanitizeText(input.name, 160);
    if (!name) return null;
    const userId = useAuthStore.getState().user?.id ?? null;
    const now = new Date().toISOString();
    const category = sanitizeCategory(input.category);
    const item: CustomJournalItem = {
      id: genId('ji'),
      userId,
      category,
      name,
      unit: sanitizeText(input.unit, 40),
      defaultDose: sanitizeNumber(input.defaultDose),
      defaultFrequency: sanitizeText(input.defaultFrequency, 160),
      mayAffectMetrics: input.mayAffectMetrics ?? category !== 'custom',
      notes: sanitizeText(input.notes),
      source: 'user',
      confidence: 'user_reported',
      createdAt: now,
      updatedAt: now,
      pendingSync: true,
    };
    const startEvent: CustomJournalEvent = {
      id: genId('je'),
      userId,
      itemId: item.id,
      eventType: 'start',
      effectiveAt: toEffectiveAt(input.startDate),
      dose: item.defaultDose,
      unit: item.unit,
      frequency: item.defaultFrequency,
      notes: item.notes,
      source: 'user',
      confidence: 'user_reported',
      createdAt: now,
      pendingSync: true,
    };
    set((state) => {
      const next = {
        items: [...state.items, item].slice(-120),
        events: [...state.events, startEvent].slice(-240),
        lastSyncAt: state.lastSyncAt,
        lastSyncError: null,
      };
      void persistSafely(next);
      return { ...next, syncStatus: 'idle' };
    });
    void get().syncPendingToSupabase();
    return item;
  },

  addEvent: async (input) => {
    const item = get().items.find((candidate) => candidate.id === input.itemId);
    if (!item) return null;
    const userId = useAuthStore.getState().user?.id ?? item.userId ?? null;
    const now = new Date().toISOString();
    const event: CustomJournalEvent = {
      id: genId('je'),
      userId,
      itemId: item.id,
      eventType: sanitizeEventType(input.eventType),
      effectiveAt: toEffectiveAt(input.effectiveAt),
      dose: sanitizeNumber(input.dose),
      unit: sanitizeText(input.unit, 40),
      frequency: sanitizeText(input.frequency, 160),
      notes: sanitizeText(input.notes),
      source: 'user',
      confidence: 'user_reported',
      createdAt: now,
      pendingSync: true,
    };
    set((state) => {
      const next = {
        items: state.items,
        events: [...state.events, event].sort((a, b) => a.effectiveAt.localeCompare(b.effectiveAt)).slice(-240),
        lastSyncAt: state.lastSyncAt,
        lastSyncError: null,
      };
      void persistSafely(next);
      return { ...next, syncStatus: 'idle' };
    });
    void get().syncPendingToSupabase();
    return event;
  },

  getActiveItems: (onDate = todayIsoDate()) => get().items.filter((item) => isItemActive(item, get().events, onDate)),
  getRecentEvents: (limit = 6) => [...get().events].sort((a, b) => b.effectiveAt.localeCompare(a.effectiveAt) || b.createdAt.localeCompare(a.createdAt)).slice(0, limit),
  countActiveMetricAffectingItems: (onDate = todayIsoDate()) => get().getActiveItems(onDate).filter((item) => item.mayAffectMetrics).length,
}));
