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
