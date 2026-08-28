/**
 * Nutrition evidence store — tracks raw evidence items (barcode scans,
 * AI photo estimates, manual entries) with a pending_review → confirmed
 * lifecycle. Only confirmed evidence feeds into normalized nutrition
 * (via addToToday on the nutrition store).
 *
 * Persistence: secureStorage, key `nutrition_evidence_v1`.
 * Rolling window: MAX_EVIDENCE items, newest first.
 * Date-scoped: hydrate drops evidence older than 7 days.
 */
import { create } from 'zustand';
import type { NutritionEvidence, NutritionEvidenceSource, NutritionEvidenceStatus } from '@lauburu/shared';
import { secureStorage } from './secure-storage';

const STORAGE_KEY = 'nutrition_evidence_v1';
const MAX_EVIDENCE = 50;
const MAX_AGE_DAYS = 7;

function genId(): string {
  return `ne-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function isWithinAgeDays(dateStr: string, maxDays: number): boolean {
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  return diff < maxDays * 86400000;
}

async function persistSafely(items: NutritionEvidence[]): Promise<void> {
  try {
    if (!items || items.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // Intentionally swallowed.
  }
}

interface NutritionEvidenceState {
  /** All evidence items, newest first. */
  items: NutritionEvidence[];
  hydrated: boolean;

  /** Load from secureStorage. Drops items older than MAX_AGE_DAYS. */
  hydrate: () => Promise<void>;

  /** Create a new evidence item in pending_review status. Returns the id. */
  addEvidence: (input: {
    source: NutritionEvidenceSource;
    raw: NutritionEvidence['raw'];
    calories?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
    fibre_g?: number | null;
    confidence?: NutritionEvidence['confidence'];
    missingFields?: string[];
  }) => string;

  /** Update macros on an existing evidence item (e.g. user edits before confirming). */
  updateEvidence: (id: string, patch: {
    calories?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
    fibre_g?: number | null;
    productName?: string | null;
    servingSize?: string | null;
  }) => void;

  /** Confirm evidence — marks it confirmed so the caller can add to nutrition. */
  confirmEvidence: (id: string) => NutritionEvidence | null;

  /** Reject evidence — marks it rejected. */
  rejectEvidence: (id: string) => void;

  /** Get today's evidence items. */
  todayItems: () => NutritionEvidence[];

  /** Get pending items for today. */
  pendingItems: () => NutritionEvidence[];
}

export const useNutritionEvidenceStore = create<NutritionEvidenceState>((set, get) => ({
  items: [],
  hydrated: false,

  hydrate: async () => {
    try {
      const raw = await secureStorage.getItem(STORAGE_KEY);
      if (!raw) {
        set({ hydrated: true });
        return;
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        await secureStorage.removeItem(STORAGE_KEY);
        set({ hydrated: true });
        return;
      }
      const items = parsed
        .filter((e: any) => e && e.id && e.date && isWithinAgeDays(e.date, MAX_AGE_DAYS))
        .slice(0, MAX_EVIDENCE) as NutritionEvidence[];
      set({ items, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },

  addEvidence: (input) => {
    const id = genId();
    const now = new Date().toISOString();
    const item: NutritionEvidence = {
      id,
      date: todayIsoDate(),
      source: input.source,
      status: 'pending_review',
      createdAt: now,
      updatedAt: now,
      raw: input.raw,
      calories: input.calories ?? null,
      protein_g: input.protein_g ?? null,
      carbs_g: input.carbs_g ?? null,
      fat_g: input.fat_g ?? null,
      fibre_g: input.fibre_g ?? null,
      confidence: input.confidence ?? null,
      missingFields: input.missingFields ?? [],
      confirmedByUser: false,
    };
    let next: NutritionEvidence[] = [];
    set((state) => {
      next = [item, ...state.items].slice(0, MAX_EVIDENCE);
      return { items: next };
    });
    void persistSafely(next);
    return id;
  },

  updateEvidence: (id, patch) => {
    let next: NutritionEvidence[] = [];
    set((state) => {
      next = state.items.map((e) => {
        if (e.id !== id) return e;
        return {
          ...e,
          calories: patch.calories !== undefined ? patch.calories : e.calories,
          protein_g: patch.protein_g !== undefined ? patch.protein_g : e.protein_g,
          carbs_g: patch.carbs_g !== undefined ? patch.carbs_g : e.carbs_g,
          fat_g: patch.fat_g !== undefined ? patch.fat_g : e.fat_g,
          fibre_g: patch.fibre_g !== undefined ? patch.fibre_g : e.fibre_g,
          raw: {
            ...e.raw,
            ...(patch.productName !== undefined ? { productName: patch.productName } : {}),
            ...(patch.servingSize !== undefined ? { servingSize: patch.servingSize } : {}),
          },
          updatedAt: new Date().toISOString(),
        };
      });
      return { items: next };
    });
    void persistSafely(next);
  },

  confirmEvidence: (id) => {
    let confirmed: NutritionEvidence | null = null;
    let next: NutritionEvidence[] = [];
    set((state) => {
      next = state.items.map((e) => {
        if (e.id !== id) return e;
        const updated = {
          ...e,
          status: 'confirmed' as NutritionEvidenceStatus,
          confirmedByUser: true,
          updatedAt: new Date().toISOString(),
        };
        confirmed = updated;
        return updated;
      });
      return { items: next };
    });
    void persistSafely(next);
    return confirmed;
  },

  rejectEvidence: (id) => {
    let next: NutritionEvidence[] = [];
    set((state) => {
      next = state.items.map((e) => {
        if (e.id !== id) return e;
        return {
          ...e,
          status: 'rejected' as NutritionEvidenceStatus,
          updatedAt: new Date().toISOString(),
        };
      });
      return { items: next };
    });
    void persistSafely(next);
  },

  todayItems: () => {
    const today = todayIsoDate();
    return get().items.filter((e) => e.date === today);
  },

  pendingItems: () => {
    const today = todayIsoDate();
    return get().items.filter((e) => e.date === today && e.status === 'pending_review');
  },
}));
