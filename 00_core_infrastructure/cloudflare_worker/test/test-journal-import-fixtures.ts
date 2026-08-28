import assert from 'node:assert/strict';
import {
  JOURNAL_CANONICAL_TERMS,
  JOURNAL_ITEM_CATEGORIES,
} from '../src/data/journal-canonical-terms';
import {
  SYNTHETIC_JOURNAL_TERM_FIXTURES,
  SYNTHETIC_LACTATE_FIXTURES,
  SYNTHETIC_MACRO_FIXTURES,
  SYNTHETIC_NUTRITION_CHECKLIST_FIXTURES,
} from './fixtures/journal-import-synthetic-fixtures';

const PRIVATE_DATA_PATTERN = /\b(aaron|test@example|phone|token|secret|password|apikey|api_key|bearer|jwt)\b/i;
const UNSAFE_INSIGHT_PATTERN = /\b(caused|cures|treats|diagnoses|you should|is safe|is dangerous|means you are recovered|means you are fatigued)\b/i;

function normalize(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function findCanonicalTerm(rawText: string) {
  const normalized = ` ${normalize(rawText)} `;
  return JOURNAL_CANONICAL_TERMS.find((term) => {
    const candidates = [term.canonical, ...term.aliases].map(normalize);
    return candidates.some((candidate) => candidate.length > 0 && normalized.includes(` ${candidate} `));
  });
}

function roundPct(value: number | null): number | null {
  return value == null || !Number.isFinite(value) ? null : Math.round(value);
}

function deriveMacroSummary(input: {
  proteinG: number | null;
  carbsG: number | null;
  fatG: number | null;
  calories: number | null;
  bodyweightKg: number | null;
}) {
  const proteinKcal = input.proteinG == null ? null : input.proteinG * 4;
  const carbsKcal = input.carbsG == null ? null : input.carbsG * 4;
  const fatKcal = input.fatG == null ? null : input.fatG * 9;
  const totalCalories =
    input.calories && input.calories > 0
      ? input.calories
      : proteinKcal != null && carbsKcal != null && fatKcal != null
        ? proteinKcal + carbsKcal + fatKcal
        : null;

  return {
    proteinKcalPct: totalCalories == null || proteinKcal == null ? null : roundPct((proteinKcal / totalCalories) * 100),
    carbsKcalPct: totalCalories == null || carbsKcal == null ? null : roundPct((carbsKcal / totalCalories) * 100),
    fatKcalPct: totalCalories == null || fatKcal == null ? null : roundPct((fatKcal / totalCalories) * 100),
    proteinGPerKg:
      input.proteinG != null && input.bodyweightKg != null && input.bodyweightKg > 0
        ? Math.round((input.proteinG / input.bodyweightKg) * 10) / 10
        : null,
  };
}

for (const fixture of SYNTHETIC_JOURNAL_TERM_FIXTURES) {
  assert.equal(PRIVATE_DATA_PATTERN.test(fixture.rawText), false, `${fixture.id} includes private-looking data`);
  assert.ok(JOURNAL_ITEM_CATEGORIES.includes(fixture.expectedCategory), `${fixture.id} has invalid expected category`);

  const match = findCanonicalTerm(fixture.rawText);
  assert.ok(match, `${fixture.id} should match a canonical term`);
  assert.equal(match?.canonical, fixture.expectedCanonical, `${fixture.id} canonical mismatch`);
  assert.equal(match?.category, fixture.expectedCategory, `${fixture.id} category mismatch`);
  assert.equal(
    match?.needsConfirmation,
    fixture.expectedNeedsConfirmation,
    `${fixture.id} needsConfirmation mismatch`,
  );
}

for (const fixture of SYNTHETIC_MACRO_FIXTURES) {
  const summary = deriveMacroSummary(fixture);
  assert.equal(summary.proteinKcalPct, fixture.expectedProteinKcalPct, `${fixture.id} protein kcal % mismatch`);
  assert.equal(summary.carbsKcalPct, fixture.expectedCarbsKcalPct, `${fixture.id} carbs kcal % mismatch`);
  assert.equal(summary.fatKcalPct, fixture.expectedFatKcalPct, `${fixture.id} fat kcal % mismatch`);
  assert.equal(summary.proteinGPerKg, fixture.expectedProteinGPerKg, `${fixture.id} protein g/kg mismatch`);
}

function parseNumberAfter(text: string, label: string): number | null {
  const normalized = text.replace(/\n/g, ',');
  const header = normalized.toLowerCase().split(',');
  const values = normalized.split(',').slice(header.length / 2);
  const idx = header.indexOf(label);
  if (idx >= 0 && values[idx] != null) {
    const parsed = Number(values[idx]);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function parseLactateMmolL(rawText: string): number | null {
  const csvValue = parseNumberAfter(rawText, 'lactate_mmol_l');
  if (csvValue != null) return csvValue;
  const match = rawText.match(/(\d+(?:\.\d+)?)\s*mmol\/l/i);
  return match ? Number(match[1]) : null;
}

function inferLactateTiming(rawText: string): string {
  const text = rawText.toLowerCase();
  if (text.includes('post')) return 'post_session';
  if (text.includes('during')) return 'during_session';
  if (text.includes('pre')) return 'pre_session';
  if (text.includes('morning')) return 'morning';
  return 'other';
}

function inferProtocol(rawText: string): string {
  const text = rawText.toLowerCase();
  if (text.includes('step_test')) return 'step_test';
  if (text.includes('ramp')) return 'ramp';
  return 'unknown';
}

function parseChecklistCount(rawText: string, category: string): { completed: number; target: number } | null {
  const csvLines = rawText.trim().split(/\n/);
  if (csvLines.length >= 2 && csvLines[0].includes('category')) {
    const row = csvLines[1].split(',');
    return { completed: Number(row[2]), target: Number(row[3]) };
  }
  const match = rawText.match(new RegExp(`${category}\\s+(\\d+(?:\\.\\d+)?)\\/(\\d+(?:\\.\\d+)?)`, 'i'));
  return match ? { completed: Number(match[1]), target: Number(match[2]) } : null;
}

for (const fixture of SYNTHETIC_LACTATE_FIXTURES) {
  assert.equal(PRIVATE_DATA_PATTERN.test(fixture.rawText), false, `${fixture.id} includes private-looking data`);
  assert.equal(UNSAFE_INSIGHT_PATTERN.test(fixture.rawText), false, `${fixture.id} includes unsafe insight wording`);
  assert.equal(parseLactateMmolL(fixture.rawText), fixture.expectedMmolL, `${fixture.id} lactate mmol/L mismatch`);
  assert.equal(inferProtocol(fixture.rawText), fixture.expectedProtocol, `${fixture.id} protocol mismatch`);
  assert.equal(inferLactateTiming(fixture.rawText), fixture.expectedTiming, `${fixture.id} timing mismatch`);
}

for (const fixture of SYNTHETIC_NUTRITION_CHECKLIST_FIXTURES) {
  assert.equal(PRIVATE_DATA_PATTERN.test(fixture.rawText), false, `${fixture.id} includes private-looking data`);
  assert.equal(UNSAFE_INSIGHT_PATTERN.test(fixture.rawText), false, `${fixture.id} includes unsafe insight wording`);
  const counts = parseChecklistCount(fixture.rawText, fixture.expectedCategory);
  assert.ok(counts, `${fixture.id} checklist count missing`);
  assert.equal(counts?.completed, fixture.expectedCompletedCount, `${fixture.id} completed count mismatch`);
  assert.equal(counts?.target, fixture.expectedTargetCount, `${fixture.id} target count mismatch`);
}

console.log(
  `journal import synthetic fixtures OK (${SYNTHETIC_JOURNAL_TERM_FIXTURES.length} terms, ${SYNTHETIC_MACRO_FIXTURES.length} macro rows, ${SYNTHETIC_LACTATE_FIXTURES.length} lactate rows, ${SYNTHETIC_NUTRITION_CHECKLIST_FIXTURES.length} checklist rows)`,
);
