import type { JournalItemCategory } from '../../src/data/journal-canonical-terms';

export interface SyntheticJournalTermFixture {
  id: string;
  sourceKind: 'apple_notes' | 'free_text' | 'generic_csv' | 'cronometer_csv';
  rawText: string;
  expectedCanonical: string;
  expectedCategory: JournalItemCategory;
  expectedNeedsConfirmation: boolean;
}

export interface SyntheticMacroFixture {
  id: string;
  sourceKind: 'cronometer_csv' | 'generic_csv' | 'manual';
  proteinG: number | null;
  carbsG: number | null;
  fatG: number | null;
  fiberG: number | null;
  calories: number | null;
  bodyweightKg: number | null;
  expectedProteinKcalPct: number | null;
  expectedCarbsKcalPct: number | null;
  expectedFatKcalPct: number | null;
  expectedProteinGPerKg: number | null;
}

export interface SyntheticLactateFixture {
  id: string;
  sourceKind: 'manual' | 'generic_csv';
  rawText: string;
  expectedMmolL: number;
  expectedProtocol: string;
  expectedTiming: 'pre_session' | 'during_session' | 'post_session' | 'morning' | 'other';
  expectedConfidence: 'user_reported' | 'imported_uncertain';
}

export interface SyntheticNutritionChecklistFixture {
  id: string;
  sourceKind: 'manual' | 'generic_csv';
  rawText: string;
  expectedCategory: string;
  expectedCompletedCount: number;
  expectedTargetCount: number;
  expectedConfidence: 'user_reported' | 'imported_uncertain';
}

export const SYNTHETIC_JOURNAL_TERM_FIXTURES: readonly SyntheticJournalTermFixture[] = [
  {
    id: 'apple-notes-bpc-alias',
    sourceKind: 'apple_notes',
    rawText: '2026-05-01: Started bpc157 note, confirm exact item before saving.',
    expectedCanonical: 'BPC-157',
    expectedCategory: 'peptide',
    expectedNeedsConfirmation: true,
  },
  {
    id: 'apple-notes-pulmicort-brand',
    sourceKind: 'apple_notes',
    rawText: '2026-05-02: Pulmicort used after dusty room; no interpretation.',
    expectedCanonical: 'Budesonide',
    expectedCategory: 'inhaler',
    expectedNeedsConfirmation: true,
  },
  {
    id: 'free-text-mouth-tape',
    sourceKind: 'free_text',
    rawText: 'Tried mouth taping during sleep, subjective note only.',
    expectedCanonical: 'Mouth tape',
    expectedCategory: 'sleep_aid',
    expectedNeedsConfirmation: false,
  },
  {
    id: 'free-text-dex-brand',
    sourceKind: 'free_text',
    rawText: 'Dexedrine timing changed; parser must require confirmation.',
    expectedCanonical: 'Dexamphetamine',
    expectedCategory: 'medication',
    expectedNeedsConfirmation: true,
  },
  {
    id: 'generic-csv-creatine',
    sourceKind: 'generic_csv',
    rawText: 'creatine monohydrate,5,g,breakfast',
    expectedCanonical: 'Creatine',
    expectedCategory: 'supplement',
    expectedNeedsConfirmation: false,
  },
  {
    id: 'free-text-salbutamol-brand',
    sourceKind: 'free_text',
    rawText: 'Ventolin note before warmup; background only.',
    expectedCanonical: 'Salbutamol',
    expectedCategory: 'inhaler',
    expectedNeedsConfirmation: true,
  },
] as const;

export const SYNTHETIC_MACRO_FIXTURES: readonly SyntheticMacroFixture[] = [
  {
    id: 'complete-cronometer-day',
    sourceKind: 'cronometer_csv',
    proteinG: 180,
    carbsG: 240,
    fatG: 80,
    fiberG: 34,
    calories: 2400,
    bodyweightKg: 90,
    expectedProteinKcalPct: 30,
    expectedCarbsKcalPct: 40,
    expectedFatKcalPct: 30,
    expectedProteinGPerKg: 2,
  },
  {
    id: 'summary-with-missing-fat',
    sourceKind: 'generic_csv',
    proteinG: 120,
    carbsG: 200,
    fatG: null,
    fiberG: 20,
    calories: 1900,
    bodyweightKg: 80,
    expectedProteinKcalPct: 25,
    expectedCarbsKcalPct: 42,
    expectedFatKcalPct: null,
    expectedProteinGPerKg: 1.5,
  },
  {
    id: 'no-bodyweight',
    sourceKind: 'manual',
    proteinG: 150,
    carbsG: 150,
    fatG: 70,
    fiberG: null,
    calories: null,
    bodyweightKg: null,
    expectedProteinKcalPct: 33,
    expectedCarbsKcalPct: 33,
    expectedFatKcalPct: 34,
    expectedProteinGPerKg: null,
  },
] as const;

export const SYNTHETIC_LACTATE_FIXTURES: readonly SyntheticLactateFixture[] = [
  {
    id: 'manual-post-session-lactate',
    sourceKind: 'manual',
    rawText: '2026-05-08 post session lactate 7.2 mmol/L, stage 4, HR 168, RPE 8, protocol ramp.',
    expectedMmolL: 7.2,
    expectedProtocol: 'ramp',
    expectedTiming: 'post_session',
    expectedConfidence: 'user_reported',
  },
  {
    id: 'csv-lactate-threshold-step',
    sourceKind: 'generic_csv',
    rawText: 'measured_at,lactate_mmol_l,protocol,stage,heart_rate_bpm,rpe,timing\n2026-05-08T07:10:00Z,3.4,step_test,stage_2,142,6,during_session',
    expectedMmolL: 3.4,
    expectedProtocol: 'step_test',
    expectedTiming: 'during_session',
    expectedConfidence: 'imported_uncertain',
  },
] as const;

export const SYNTHETIC_NUTRITION_CHECKLIST_FIXTURES: readonly SyntheticNutritionChecklistFixture[] = [
  {
    id: 'manual-daily-dozen-greens',
    sourceKind: 'manual',
    rawText: 'Daily checklist: greens 2/2, berries 1/1, whole grains 2/3.',
    expectedCategory: 'greens',
    expectedCompletedCount: 2,
    expectedTargetCount: 2,
    expectedConfidence: 'user_reported',
  },
  {
    id: 'csv-daily-dozen-legumes',
    sourceKind: 'generic_csv',
    rawText: 'date,category,completed_count,target_count\n2026-05-08,beans_legumes,1,3',
    expectedCategory: 'beans_legumes',
    expectedCompletedCount: 1,
    expectedTargetCount: 3,
    expectedConfidence: 'imported_uncertain',
  },
] as const;
