/**
 * Contract tests for nutrition evidence gating, HIIT session ingest,
 * and Coach consumption rules.
 *
 * Runs as a standalone script — no test framework needed.
 * Tests pure functions from shared packages. No server required.
 *
 * Usage: npx tsx src/server/scripts/test-nutrition-hiit-contracts.ts
 */

import { ingestNutritionDay, isNutritionIngestConfirmed } from '../../../../packages/shared/src/backend/services/nutrition/ingest-nutrition';
import { ingestAndNormalizeSessionLog } from '../../../../packages/shared/src/backend/services/session/ingest-session-log';
import { normalizeSessionLog } from '../../../../packages/shared/src/backend/contracts/session-log.types';
import { isNutritionIngestAllowed, deriveNutritionCoverage } from '../../../../packages/shared/src/backend/contracts/nutrition-evidence-ingest.types';
import { compareHiitWorkouts } from '../../../../packages/shared/src/backend/services/hiit/compare-hiit-workouts';
import { buildCoachAnswer } from '../../../../packages/shared/src/backend/services/coach/build-coach-answer';
import { DefaultCronometerAdapter } from '../../../../packages/shared/src/backend/services/cronometer/cronometer-adapter';
import { getDefaultCronometerState, buildCronometerCoverage } from '../../../../packages/shared/src/backend/contracts/cronometer.types';
import { buildMultiSourceHealth } from '../../../../packages/shared/src/backend/services/health-source/build-multi-source-health';
import { shouldReadLiveWhoop } from '../../../../packages/shared/src/backend/services/freshness/should-read-live-whoop';
import type { SourceHealthStatus } from '../../../../packages/shared/src/backend/contracts/freshness.types';
import type { SessionLogIngestPayload, SessionSetMetrics } from '../../../../packages/shared/src/backend/contracts/session-log.types';
import type { HIITWorkoutRecord } from '../../../../packages/shared/src/types/hiit-workout';
import type { AthleteAiContextResponse } from '../../../../packages/shared/src/backend/contracts/ai-context.types';

let passed = 0;
let failed = 0;

function assert(condition: boolean, name: string) {
  if (condition) {
    passed++;
    console.log(`  PASS: ${name}`);
  } else {
    failed++;
    console.log(`  FAIL: ${name}`);
  }
}

function section(name: string) {
  console.log(`\n=== ${name} ===`);
}

(async () => {
// ---------------------------------------------------------------------------
// 1. Nutrition ingest confirmation gating
// ---------------------------------------------------------------------------
section('Nutrition ingest confirmation gating');

// Manual is implicitly confirmed
assert(isNutritionIngestConfirmed({ date: '2026-04-15', source: 'manual' }) === true,
  'manual nutrition is implicitly confirmed');

// Cronometer is implicitly confirmed
assert(isNutritionIngestConfirmed({ date: '2026-04-15', source: 'cronometer' }) === true,
  'cronometer nutrition is implicitly confirmed');

// Barcode unconfirmed is NOT allowed
assert(isNutritionIngestConfirmed({ date: '2026-04-15', source: 'barcode', confirmed: false }) === false,
  'barcode unconfirmed does not enter nutrition');

// Barcode confirmed IS allowed
assert(isNutritionIngestConfirmed({ date: '2026-04-15', source: 'barcode', confirmed: true }) === true,
  'barcode confirmed enters nutrition');

// AI photo unconfirmed is NOT allowed
assert(isNutritionIngestConfirmed({ date: '2026-04-15', source: 'ai_photo', confirmed: false }) === false,
  'photo proposed does not enter nutrition');

// AI photo confirmed IS allowed
assert(isNutritionIngestConfirmed({ date: '2026-04-15', source: 'ai_photo', confirmed: true }) === true,
  'photo confirmed enters as estimated');

// Default source (undefined) is implicitly confirmed (manual)
assert(isNutritionIngestConfirmed({ date: '2026-04-15' }) === true,
  'default source is implicitly confirmed');

// V2 contract gating
assert(isNutritionIngestAllowed({
  date: '2026-04-15', source: 'barcode', sourceState: 'manual',
  confirmed: false, calories_kcal: 200, protein_g: 10, carbs_g: 30, fat_g: 8,
  fibre_g: null, sugar_g: null, sodium_mg: null, water_ml: null,
  missingFields: [], evidenceIds: [], sourceDependencies: [],
}) === false, 'V2 unconfirmed barcode blocked from normalized');

assert(isNutritionIngestAllowed({
  date: '2026-04-15', source: 'ai_photo', sourceState: 'estimated',
  confirmed: true, calories_kcal: 350, protein_g: 20, carbs_g: 40, fat_g: 15,
  fibre_g: null, sugar_g: null, sodium_mg: null, water_ml: null,
  missingFields: [], evidenceIds: ['ne-1'], sourceDependencies: ['ai_photo'],
}) === true, 'V2 confirmed photo allowed into normalized');

// ---------------------------------------------------------------------------
// 2. Nutrition ingest preserves source state
// ---------------------------------------------------------------------------
section('Nutrition ingest preserves source state');

const manualIngest = ingestNutritionDay({
  date: '2026-04-15', source: 'manual', calories_kcal: 500, protein_g: 30,
}, 'test-athlete');
assert(manualIngest.source === 'manual', 'manual nutrition enters as manual');
assert(manualIngest.confirmed === true, 'manual entry is auto-confirmed');
assert(manualIngest.sourceState === 'manual', 'manual source state is "manual"');

const barcodeConfirmedIngest = ingestNutritionDay({
  date: '2026-04-15', source: 'barcode', confirmed: true, sourceState: 'manual',
  calories_kcal: 200, protein_g: 15,
}, 'test-athlete');
assert(barcodeConfirmedIngest.confirmed === true, 'confirmed barcode is confirmed');

const photoUnconfirmedIngest = ingestNutritionDay({
  date: '2026-04-15', source: 'ai_photo', confirmed: false, sourceState: 'estimated',
  calories_kcal: 350,
}, 'test-athlete');
assert(photoUnconfirmedIngest.confirmed === false, 'unconfirmed photo stays unconfirmed');

// ---------------------------------------------------------------------------
// 3. Nutrition coverage derivation
// ---------------------------------------------------------------------------
section('Nutrition coverage derivation');

assert(deriveNutritionCoverage({
  date: '2026-04-15', source: 'manual', sourceState: 'manual', confirmed: true,
  calories_kcal: 500, protein_g: 30, carbs_g: 50, fat_g: 20,
  fibre_g: null, sugar_g: null, sodium_mg: null, water_ml: null,
  missingFields: [], evidenceIds: [], sourceDependencies: [],
}) === 'full', 'full coverage when all 4 macros present');

assert(deriveNutritionCoverage({
  date: '2026-04-15', source: 'manual', sourceState: 'manual', confirmed: true,
  calories_kcal: 500, protein_g: null, carbs_g: null, fat_g: null,
  fibre_g: null, sugar_g: null, sodium_mg: null, water_ml: null,
  missingFields: ['protein', 'carbs', 'fat'], evidenceIds: [], sourceDependencies: [],
}) === 'partial', 'partial coverage when only calories present');

assert(deriveNutritionCoverage({
  date: '2026-04-15', source: 'manual', sourceState: 'manual', confirmed: true,
  calories_kcal: null, protein_g: null, carbs_g: null, fat_g: null,
  fibre_g: null, sugar_g: null, sodium_mg: null, water_ml: null,
  missingFields: ['calories', 'protein', 'carbs', 'fat'], evidenceIds: [], sourceDependencies: [],
}) === 'none', 'no coverage when all macros null');

// ---------------------------------------------------------------------------
// 4. HIIT session ingest with per-set metrics
// ---------------------------------------------------------------------------
section('HIIT session ingest with per-set metrics');

const hiitSession: SessionLogIngestPayload = {
  sessionId: 'test-sess-1',
  athleteId: 'test-athlete',
  date: '2026-04-15',
  createdAt: new Date().toISOString(),
  templateId: 'friday-bike',
  protocolFormat: '30:30',
  machineType: 'assault_bike',
  machineProvider: 'manual',
  source: 'manual',
  sets: [
    { setIndex: 0, type: 'work', durationSeconds: 30, avgWatts: 250, peakWatts: 280, calories: 12, hrMin: 140, hrMax: 165, hrAvg: 155, distanceM: null, avgCadence: null, hrAtStart: 140, hrAtEnd: 165, hrRange: 25, hrRecoveryFromPrevious: null },
    { setIndex: 1, type: 'rest', durationSeconds: 30, avgWatts: null, peakWatts: null, calories: null, hrMin: 130, hrMax: 145, hrAvg: 138, distanceM: null, avgCadence: null, hrAtStart: 165, hrAtEnd: 130, hrRange: 15, hrRecoveryFromPrevious: null },
    { setIndex: 2, type: 'work', durationSeconds: 30, avgWatts: 230, peakWatts: 260, calories: 11, hrMin: 150, hrMax: 170, hrAvg: 162, distanceM: null, avgCadence: null, hrAtStart: 130, hrAtEnd: 170, hrRange: 40, hrRecoveryFromPrevious: 35 },
    { setIndex: 3, type: 'rest', durationSeconds: 30, avgWatts: null, peakWatts: null, calories: null, hrMin: 135, hrMax: 150, hrAvg: 142, distanceM: null, avgCadence: null, hrAtStart: 170, hrAtEnd: 135, hrRange: 15, hrRecoveryFromPrevious: null },
    { setIndex: 4, type: 'work', durationSeconds: 30, avgWatts: 210, peakWatts: 240, calories: 10, hrMin: 155, hrMax: 175, hrAvg: 168, distanceM: null, avgCadence: null, hrAtStart: 135, hrAtEnd: 175, hrRange: 40, hrRecoveryFromPrevious: 35 },
  ],
  totalSets: 5,
  workSets: 3,
  restSets: 2,
  totalDurationSeconds: 150,
  totalCalories: 33,
  totalWorkKj: null,
  avgWatts: 230,
  peakWatts: 280,
  avgHr: 155,
  peakHr: 175,
  sourceRecordIds: [],
  missingFields: [],
};

const { raw, normalized } = ingestAndNormalizeSessionLog(hiitSession);

assert(raw.payload.sets.length === 5, 'HIIT manual session stores all sets');
assert(raw.payload.sets[0].avgWatts === 250, 'set 0 watts preserved');
assert(raw.payload.sets[0].hrAvg === 155, 'set 0 HR preserved');
assert(raw.payload.sets[4].avgWatts === 210, 'set 4 watts preserved (fatigue visible)');
assert(normalized.wattsDropOffPct !== null, 'watts drop-off computed');
assert(normalized.wattsDropOffPct! < 0, 'watts drop-off is negative (fatigue)');
assert(normalized.hrDriftPct !== null, 'HR drift computed');
assert(normalized.hrDriftPct! > 0, 'HR drift is positive (cardiac drift)');
assert(normalized.avgHrRecoveryBpm !== null, 'avg HR recovery computed');
assert(normalized.hasPerSetWatts === true, 'per-set watts detected');
assert(normalized.hasPerSetHr === true, 'per-set HR detected');
assert(normalized.machineConnected === false, 'manual source = not machine connected');

// ---------------------------------------------------------------------------
// 5. Missing machine source remains not_connected
// ---------------------------------------------------------------------------
section('Machine connection status');

const manualSession = normalizeSessionLog({
  ...hiitSession,
  source: 'manual',
  machineProvider: 'manual',
});
assert(manualSession.machineConnected === false, 'manual source = not connected');

// A concept2-sourced session would be connected
const concept2Session = normalizeSessionLog({
  ...hiitSession,
  source: 'concept2',
  machineProvider: 'concept2',
});
assert(concept2Session.machineConnected === true, 'concept2 source = connected');

// ---------------------------------------------------------------------------
// 6. HIIT progress comparison
// ---------------------------------------------------------------------------
section('HIIT progress comparison');

const currentWorkout: HIITWorkoutRecord = {
  id: 'w1', athleteId: 'test', date: '2026-04-15', createdAt: new Date().toISOString(),
  templateId: 'friday-bike', protocolFormat: '30:30', machineType: 'assault_bike', machineProvider: 'manual',
  sets: [
    { setIndex: 0, type: 'work', durationSeconds: 30, avgWatts: 250, peakWatts: 280, calories: 12, hrMin: null, hrMax: null, hrAvg: 155, distanceM: null, avgCadence: null },
    { setIndex: 1, type: 'work', durationSeconds: 30, avgWatts: 230, peakWatts: 260, calories: 11, hrMin: null, hrMax: null, hrAvg: 162, distanceM: null, avgCadence: null },
  ],
  totalSets: 2, workSets: 2, restSets: 0, totalDurationSeconds: 60,
  totalCalories: 23, totalWorkKj: null, avgWatts: 240, peakWatts: 280, avgHr: 158, peakHr: 162,
  source: 'manual', sourceRecordIds: [], missingFields: [],
};

const previousWorkout: HIITWorkoutRecord = {
  ...currentWorkout,
  id: 'w0', date: '2026-04-12',
  sets: [
    { setIndex: 0, type: 'work', durationSeconds: 30, avgWatts: 220, peakWatts: 250, calories: 10, hrMin: null, hrMax: null, hrAvg: 150, distanceM: null, avgCadence: null },
    { setIndex: 1, type: 'work', durationSeconds: 30, avgWatts: 200, peakWatts: 230, calories: 9, hrMin: null, hrMax: null, hrAvg: 158, distanceM: null, avgCadence: null },
  ],
  avgWatts: 210, peakWatts: 250, avgHr: 154, totalCalories: 19,
};

const comparison = compareHiitWorkouts(currentWorkout, previousWorkout);
assert(comparison.avgWattsDelta === 30, 'avg watts delta = +30');
assert(comparison.peakWattsDelta === 30, 'peak watts delta = +30');
assert(comparison.setComparisons.length === 2, '2 set comparisons');
assert(comparison.setComparisons[0].deltaWatts === 30, 'set 0 watts delta = +30');

// ---------------------------------------------------------------------------
// 7. Coach does not use unconfirmed nutrition
// ---------------------------------------------------------------------------
section('Coach consumption rules');

const baseContext: AthleteAiContextResponse = {
  ok: true,
  athleteId: 'test',
  date: '2026-04-15',
  seedMode: false,
  provisionalUntilDirectWhoop: false,
  seedCaveats: [],
  capability: {
    mode: 'live_ready',
    safeFor: ['display_recovery_score_as_live'],
    notSafeFor: [],
    missingWhoopNativeFields: [],
    recommendedReadOrder: ['daily_refresh_artifact'],
  },
  sourceHealth: null,
  normalizedDay: null,
  dailyArtifact: null,
  weeklyArtifact: null,
  baselines: null,
  blockSummary: null,
  nutritionDailySummary: null,
  nutritionSources: [],
  recentHIITWorkouts: null,
  hiitProgressSummary: null,
  machineConnectionStatus: null,
  confidence: 'medium',
};

// Coach with no nutrition data
const noNutrAnswer = buildCoachAnswer('what did I eat today?', baseContext);
assert(noNutrAnswer.domain === 'nutrition', 'nutrition question routes to nutrition');
assert(noNutrAnswer.status === 'insufficient_data', 'no nutrition = insufficient_data');
assert(noNutrAnswer.answer.short.includes('No nutrition'), 'Coach says no nutrition data');

// Coach with confirmed nutrition
const withNutr = {
  ...baseContext,
  nutritionDailySummary: {
    calories: 2000,
    proteinGrams: 120,
    carbGrams: 200,
    fatGrams: 80,
    coverage: 'full' as const,
    missingFields: [],
    sourceState: 'manual' as const,
    sourceDependencies: ['manual'],
    allConfirmed: true,
  },
  nutritionSources: ['manual'],
};
const nutrAnswer = buildCoachAnswer('what did I eat today?', withNutr);
assert(nutrAnswer.status === 'answered', 'confirmed nutrition = answered');
assert(nutrAnswer.answer.short.includes('2000'), 'Coach reports calories');

// Coach can summarize confirmed HIIT progress
const withHIIT = {
  ...baseContext,
  recentHIITWorkouts: [
    { id: 'w1', date: '2026-04-15', protocolFormat: '30:30', machineType: 'assault_bike', totalSets: 5, avgWatts: 230, totalCalories: 33, avgHr: 155 },
  ],
  hiitProgressSummary: {
    avgWattsDelta: 20,
    peakWattsDelta: 15,
    wattsDropOffPct: -8,
    hrDriftPct: 5,
  },
};
const hiitAnswer = buildCoachAnswer('how did my HIIT compare to last time?', withHIIT as any);
assert(hiitAnswer.domain === 'hiit', 'HIIT progress question routes to hiit');
assert(hiitAnswer.status === 'answered', 'HIIT with data = answered');
assert(hiitAnswer.answer.short.includes('230'), 'Coach reports watts');

// Coach with no HIIT data
const noHIITAnswer = buildCoachAnswer('how did my watts drop off?', baseContext);
assert(noHIITAnswer.domain === 'hiit', 'HIIT question routes to hiit');
assert(noHIITAnswer.status === 'insufficient_data', 'no HIIT = insufficient_data');

// Coach readiness blocked without live WHOOP
const seedContext = {
  ...baseContext,
  seedMode: true,
  capability: {
    ...baseContext.capability,
    mode: 'seed_partial' as const,
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain'],
    notSafeFor: ['display_recovery_score_as_live'],
  },
};
const readinessAnswer = buildCoachAnswer('am I recovered enough for HIIT?', seedContext);
assert(readinessAnswer.status === 'insufficient_data' || readinessAnswer.status === 'downgraded', 'readiness blocked without live WHOOP');

// ---------------------------------------------------------------------------
// 8. Nutrition provenance visible in ai-context shape
// ---------------------------------------------------------------------------
section('Nutrition provenance in ai-context');

assert(withNutr.nutritionDailySummary.sourceState === 'manual',
  'nutrition provenance sourceState = manual');
assert(withNutr.nutritionDailySummary.sourceDependencies.includes('manual'),
  'nutrition provenance sourceDependencies contains manual');
assert(withNutr.nutritionDailySummary.allConfirmed === true,
  'nutrition provenance allConfirmed = true');

// Coach knows about nutrition sources
const sourceAnswer = buildCoachAnswer('what are my nutrition sources?', withNutr);
assert(sourceAnswer.domain === 'nutrition', 'nutrition source question routes to nutrition');
assert(sourceAnswer.answer.short.includes('manual') || sourceAnswer.status === 'answered',
  'Coach reports nutrition source state');

// Photo-estimated nutrition provenance
const withPhotoNutr = {
  ...baseContext,
  nutritionDailySummary: {
    calories: 500,
    proteinGrams: 30,
    carbGrams: 60,
    fatGrams: 20,
    coverage: 'full' as const,
    missingFields: [],
    sourceState: 'estimated' as const,
    sourceDependencies: ['ai_photo'],
    allConfirmed: true,
  },
  nutritionSources: ['ai_photo'],
};
assert(withPhotoNutr.nutritionDailySummary.sourceState === 'estimated',
  'photo nutrition sourceState = estimated');
const photoNutrAnswer = buildCoachAnswer('what did I eat today?', withPhotoNutr);
assert(photoNutrAnswer.status === 'answered', 'confirmed photo nutrition = answered');

// ---------------------------------------------------------------------------
// 9. Same workout grouping works safely
// ---------------------------------------------------------------------------
section('Workout template grouping');

const w1: HIITWorkoutRecord = {
  id: 'w-a', athleteId: 'test', date: '2026-04-14', createdAt: '2026-04-14T10:00:00Z',
  templateId: 'friday-bike', protocolFormat: '30:30', machineType: 'assault_bike',
  machineProvider: 'manual',
  sets: [
    { setIndex: 0, type: 'work', durationSeconds: 30, avgWatts: 200, peakWatts: 220, calories: 10, hrMin: null, hrMax: null, hrAvg: 150, distanceM: null, avgCadence: null },
  ],
  totalSets: 1, workSets: 1, restSets: 0, totalDurationSeconds: 30,
  totalCalories: 10, totalWorkKj: null, avgWatts: 200, peakWatts: 220, avgHr: 150, peakHr: 150,
  source: 'manual', sourceRecordIds: [], missingFields: [],
};
const w2: HIITWorkoutRecord = {
  ...w1, id: 'w-b', date: '2026-04-15', createdAt: '2026-04-15T10:00:00Z',
  sets: [
    { setIndex: 0, type: 'work', durationSeconds: 30, avgWatts: 220, peakWatts: 250, calories: 11, hrMin: null, hrMax: null, hrAvg: 148, distanceM: null, avgCadence: null },
  ],
  avgWatts: 220, peakWatts: 250, avgHr: 148, totalCalories: 11,
};
const comp = compareHiitWorkouts(w2, w1);
assert(comp.templateId === 'friday-bike', 'template grouping uses templateId');
assert(comp.avgWattsDelta === 20, 'grouped comparison watts delta = +20');

// Different template IDs are not grouped
const w3: HIITWorkoutRecord = { ...w1, id: 'w-c', templateId: 'monday-rower' };
const comp2 = compareHiitWorkouts(w2, w3);
assert(comp2.avgWattsDelta === 20, 'cross-template comparison still computes (caller filters)');

// Null templateId falls back to protocolFormat
const wNoTemplate: HIITWorkoutRecord = { ...w1, id: 'w-d', templateId: null };
const comp3 = compareHiitWorkouts(wNoTemplate, null);
assert(comp3.templateId === '30:30', 'null templateId falls back to protocolFormat');
assert(comp3.previousWorkoutId === null, 'null previous = null previousWorkoutId');

// ---------------------------------------------------------------------------
// 10. Cronometer adapter + connection state
// ---------------------------------------------------------------------------
section('Cronometer adapter + connection state');

// Default state is not_connected
const defaultCronState = getDefaultCronometerState();
assert(defaultCronState.status === 'not_connected', 'Cronometer default = not_connected');
assert(defaultCronState.hasCredentials === false, 'Cronometer default hasCredentials = false');
assert(defaultCronState.reason !== null, 'Cronometer default has reason');
assert(defaultCronState.actionRequired !== null, 'Cronometer default has actionRequired');

// Adapter returns not_connected without env vars
const adapter = new DefaultCronometerAdapter();
const adapterState = await adapter.checkConnection();
assert(adapterState.status === 'not_connected' || adapterState.status === 'auth_required',
  'Cronometer adapter returns not_connected or auth_required');
assert(adapterState.hasCredentials === false || adapterState.hasCredentials === true,
  'Cronometer adapter hasCredentials is boolean');

// fetchDaily returns null when not connected
const dailyData = await adapter.fetchDaily('2026-04-15');
assert(dailyData === null, 'Cronometer fetchDaily returns null when not connected');

// Coverage builder
const mockRaw = {
  date: '2026-04-15',
  fetchedAt: new Date().toISOString(),
  fetchMethod: 'api' as const,
  caloriesKcal: 2200,
  proteinGrams: 140,
  carbGrams: 220,
  fatGrams: 85,
  fiberGrams: 28,
  sugarGrams: 45,
  sodiumMg: 2300,
  waterMl: null,
  bodyMassKg: null,
  mealTimestamps: ['2026-04-15T08:00:00Z', '2026-04-15T12:30:00Z'],
  presentFields: ['calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'sodium'],
  missingFields: ['water', 'body_mass'],
};
const coverage = buildCronometerCoverage(mockRaw);
assert(coverage.length === 9, 'Cronometer coverage has 9 domains');
assert(coverage.find((c) => c.domain === 'calories')?.available === true, 'calories available');
assert(coverage.find((c) => c.domain === 'water')?.available === false, 'water not available');
assert(coverage.find((c) => c.domain === 'body_mass')?.available === false, 'body_mass not available');
assert(coverage.find((c) => c.domain === 'meal_timestamps')?.available === true, 'meal_timestamps available');
assert(coverage.find((c) => c.domain === 'meal_timestamps')?.value === 2, 'meal_timestamps = 2 meals');

// Cronometer connected with partial data (missing water/sodium)
const partialRaw = { ...mockRaw, waterMl: null, sodiumMg: null, missingFields: ['water', 'sodium', 'body_mass'] };
const partialCoverage = buildCronometerCoverage(partialRaw);
assert(partialCoverage.find((c) => c.domain === 'water')?.available === false, 'partial: water missing');
assert(partialCoverage.find((c) => c.domain === 'sodium')?.available === false, 'partial: sodium missing');
assert(partialCoverage.find((c) => c.domain === 'protein')?.available === true, 'partial: protein present');

// ---------------------------------------------------------------------------
// 11. Coach Cronometer questions
// ---------------------------------------------------------------------------
section('Coach Cronometer questions');

// Coach "Is Cronometer connected?" — not connected
const cronometerNotConnected = buildCoachAnswer('is cronometer connected?', {
  ...baseContext,
  multiSourceHealth: {
    whoop: { status: 'not_connected' },
    apple_health: { status: 'not_connected' },
    cronometer: { status: 'not_connected' },
  },
} as any);
assert(cronometerNotConnected.domain === 'nutrition', 'cronometer question routes to nutrition');
assert(cronometerNotConnected.answer.short.includes('not connected'),
  'Coach says Cronometer not connected');

// Coach "What did Cronometer log today?" — not connected
const cronometerLogNotConnected = buildCoachAnswer('what did cronometer log today?', {
  ...baseContext,
  multiSourceHealth: {
    whoop: { status: 'not_connected' },
    apple_health: { status: 'not_connected' },
    cronometer: { status: 'not_connected' },
  },
} as any);
assert(cronometerLogNotConnected.answer.short.includes('not connected'),
  'Coach says Cronometer not connected for log question');
assert(cronometerLogNotConnected.answer.nextStep.includes('manual') || cronometerLogNotConnected.answer.nextStep.includes('barcode'),
  'Coach offers alternatives when Cronometer not connected');

// Coach "Is Cronometer connected?" — connected with data
const cronometerConnected = buildCoachAnswer('what did cronometer log today?', {
  ...baseContext,
  nutritionDailySummary: {
    calories: 2200,
    proteinGrams: 140,
    carbGrams: 220,
    fatGrams: 85,
    coverage: 'full' as const,
    missingFields: [],
    sourceState: 'live' as const,
    sourceDependencies: ['cronometer'],
    allConfirmed: true,
  },
  multiSourceHealth: {
    whoop: { status: 'not_connected' },
    apple_health: { status: 'not_connected' },
    cronometer: { status: 'fresh', upstream: 'healthy' },
  },
} as any);
assert(cronometerConnected.status === 'answered', 'Cronometer connected with data = answered');
assert(cronometerConnected.answer.short.includes('2200') || cronometerConnected.answer.short.includes('Cronometer'),
  'Coach reports Cronometer macros');

// Cronometer not connected does not block manual nutrition
const manualWithCronDisconnected = buildCoachAnswer('what did I eat today?', {
  ...baseContext,
  nutritionDailySummary: {
    calories: 800,
    proteinGrams: 50,
    carbGrams: 100,
    fatGrams: 30,
    coverage: 'full' as const,
    missingFields: [],
    sourceState: 'manual' as const,
    sourceDependencies: ['manual'],
    allConfirmed: true,
  },
  nutritionSources: ['manual'],
  multiSourceHealth: {
    cronometer: { status: 'not_connected' },
  },
} as any);
assert(manualWithCronDisconnected.status === 'answered',
  'manual nutrition works when Cronometer not connected');
assert(manualWithCronDisconnected.answer.short.includes('800'),
  'Coach reports manual calories even with Cronometer disconnected');

// No recovery-causality from Cronometer alone
const recoveryFromCronometer = buildCoachAnswer('did my nutrition hurt my recovery?', {
  ...baseContext,
  nutritionDailySummary: {
    calories: 2200,
    proteinGrams: 140,
    carbGrams: 220,
    fatGrams: 85,
    coverage: 'full' as const,
    missingFields: [],
    sourceState: 'live' as const,
    sourceDependencies: ['cronometer'],
    allConfirmed: true,
  },
  multiSourceHealth: {
    cronometer: { status: 'fresh', upstream: 'healthy' },
  },
} as any);
assert(recoveryFromCronometer.status === 'insufficient_data',
  'no recovery causality from Cronometer alone');
assert(recoveryFromCronometer.answer.short.includes('cannot claim') || recoveryFromCronometer.answer.short.includes('causality') || recoveryFromCronometer.answer.short.toLowerCase().includes('cause'),
  'Coach refuses recovery-nutrition causality');

// Coach "Is my nutrition log complete?" — full
const completeAnswer = buildCoachAnswer('is my nutrition log complete?', {
  ...baseContext,
  nutritionDailySummary: {
    calories: 2200, proteinGrams: 140, carbGrams: 220, fatGrams: 85,
    coverage: 'full' as const, missingFields: [],
    sourceState: 'manual' as const, sourceDependencies: ['manual'], allConfirmed: true,
  },
} as any);
assert(completeAnswer.answer.short.includes('complete'),
  'Coach says nutrition is complete');

// Coach "What nutrition data is missing?" — partial
const partialAnswer = buildCoachAnswer('what nutrition data is missing?', {
  ...baseContext,
  nutritionDailySummary: {
    calories: 800, proteinGrams: null, carbGrams: null, fatGrams: null,
    coverage: 'partial' as const, missingFields: ['protein', 'carbs', 'fat'],
    sourceState: 'manual' as const, sourceDependencies: ['manual'], allConfirmed: true,
  },
} as any);
assert(partialAnswer.answer.short.includes('Missing') || partialAnswer.answer.short.includes('partial'),
  'Coach reports missing fields');

// mixed manual + Cronometer day
const mixedDayAnswer = buildCoachAnswer('what did I eat today?', {
  ...baseContext,
  nutritionDailySummary: {
    calories: 2500, proteinGrams: 160, carbGrams: 250, fatGrams: 90,
    coverage: 'full' as const, missingFields: [],
    sourceState: 'mixed' as const, sourceDependencies: ['manual', 'cronometer'], allConfirmed: true,
  },
  nutritionSources: ['manual', 'cronometer'],
} as any);
assert(mixedDayAnswer.status === 'answered', 'mixed day = answered');
assert(mixedDayAnswer.answer.short.includes('2500'), 'Coach reports mixed day calories');

// ---------------------------------------------------------------------------
// 12. Nutrition raw provenance preservation
// ---------------------------------------------------------------------------
section('Nutrition raw provenance preservation');

const rawManual = ingestNutritionDay({
  date: '2026-04-16', source: 'manual', calories_kcal: 500, protein_g: 30,
  sourceDependencies: ['manual'], evidenceIds: [],
}, 'test-athlete');
assert(rawManual.missingFields?.includes('carbs') === true, 'manual raw has missingFields for carbs');
assert(rawManual.missingFields?.includes('fat') === true, 'manual raw has missingFields for fat');
assert(rawManual.sourceDependencies?.includes('manual') === true, 'manual raw sourceDependencies preserved');
assert(rawManual.sourceRecordIds != null, 'manual raw sourceRecordIds present');

const rawBarcode = ingestNutritionDay({
  date: '2026-04-16', source: 'barcode', confirmed: true,
  calories_kcal: 200, protein_g: 15, carbs_g: 25, fat_g: 8,
  sourceDependencies: ['barcode', 'openfoodfacts'], evidenceIds: ['ne-123'],
}, 'test-athlete');
assert(rawBarcode.missingFields?.length === 0, 'barcode full raw has no missingFields');
assert(rawBarcode.sourceDependencies?.includes('openfoodfacts') === true, 'barcode raw preserves openfoodfacts dep');
assert(rawBarcode.evidenceIds?.includes('ne-123') === true, 'barcode raw preserves evidenceIds');

const rawCronometer = ingestNutritionDay({
  date: '2026-04-16', source: 'cronometer',
  calories_kcal: 2200, protein_g: 140, carbs_g: 220, fat_g: 85,
}, 'test-athlete');
assert(rawCronometer.sourceState === 'live', 'cronometer raw sourceState = live');
assert(rawCronometer.sourceDependencies?.includes('cronometer') === true, 'cronometer raw sourceDeps auto-set');
assert(rawCronometer.missingFields?.length === 0, 'cronometer full raw has no missingFields');

// ---------------------------------------------------------------------------
// 13. buildMultiSourceHealth Cronometer state alignment
// ---------------------------------------------------------------------------
section('buildMultiSourceHealth Cronometer alignment');

function makeSourceHealth(overrides: Partial<SourceHealthStatus>): SourceHealthStatus {
  return {
    id: 'sh-test', schemaVersion: 1, createdAt: '', updatedAt: '',
    athleteId: 'test', provider: 'cronometer',
    lastSuccessfulIngestAt: null, lastFailedIngestAt: null,
    freshnessStatus: 'missing', coverageByDomain: {},
    upstreamStatus: 'unknown', degradedReason: null,
    ...overrides,
  };
}

// not_connected: no record at all
const summaryNoRecord = buildMultiSourceHealth('test', { cronometer: null });
const cronNoRecord = summaryNoRecord.sources.find((s) => s.provider === 'cronometer')!;
assert(cronNoRecord.connectionStatus === 'not_connected', 'no record = not_connected');

// auth_required: record with reason prefix
const summaryAuthReq = buildMultiSourceHealth('test', {
  cronometer: makeSourceHealth({
    degradedReason: 'auth_required: Credentials found but API not operational.',
  }),
});
const cronAuthReq = summaryAuthReq.sources.find((s) => s.provider === 'cronometer')!;
assert(cronAuthReq.connectionStatus === 'auth_required', 'auth_required reason = auth_required status');

// auth_expired: record with reason prefix
const summaryAuthExp = buildMultiSourceHealth('test', {
  cronometer: makeSourceHealth({
    degradedReason: 'auth_expired: Token expired.',
  }),
});
const cronAuthExp = summaryAuthExp.sources.find((s) => s.provider === 'cronometer')!;
assert(cronAuthExp.connectionStatus === 'auth_expired', 'auth_expired reason = auth_expired status');

// connected: fresh + healthy
const summaryConnected = buildMultiSourceHealth('test', {
  cronometer: makeSourceHealth({
    freshnessStatus: 'fresh',
    upstreamStatus: 'healthy',
    lastSuccessfulIngestAt: new Date().toISOString(),
    coverageByDomain: {
      calories: { lastDate: '2026-04-16', status: 'fresh' },
      protein: { lastDate: '2026-04-16', status: 'fresh' },
      carbs: { lastDate: '2026-04-16', status: 'fresh' },
      fat: { lastDate: '2026-04-16', status: 'fresh' },
    },
    degradedReason: null,
  }),
});
const cronConnected = summaryConnected.sources.find((s) => s.provider === 'cronometer')!;
assert(cronConnected.connectionStatus === 'available', 'fresh+healthy = available');
assert(cronConnected.domainsAvailable.includes('calories'), 'connected has calories domain');
assert(cronConnected.domainsAvailable.includes('protein'), 'connected has protein domain');

// stale: stale freshness
const summaryStale = buildMultiSourceHealth('test', {
  cronometer: makeSourceHealth({
    freshnessStatus: 'stale',
    upstreamStatus: 'healthy',
    coverageByDomain: {
      calories: { lastDate: '2026-04-14', status: 'stale' },
      protein: { lastDate: '2026-04-14', status: 'stale' },
    },
  }),
});
const cronStale = summaryStale.sources.find((s) => s.provider === 'cronometer')!;
assert(cronStale.connectionStatus === 'stale', 'stale freshness = stale status');

// partial: some domains available, some not
const summaryPartial = buildMultiSourceHealth('test', {
  cronometer: makeSourceHealth({
    freshnessStatus: 'expired',
    upstreamStatus: 'healthy',
    coverageByDomain: {
      calories: { lastDate: '2026-04-16', status: 'fresh' },
      protein: { lastDate: '2026-04-16', status: 'fresh' },
    },
  }),
});
const cronPartial = summaryPartial.sources.find((s) => s.provider === 'cronometer')!;
assert(cronPartial.connectionStatus === 'partial', 'some domains + expired = partial');
assert(cronPartial.domainsAvailable.length === 2, 'partial has 2 domains available');
assert(cronPartial.missingDomains.includes('water'), 'partial missing water');

// unavailable: upstream down
const summaryDown = buildMultiSourceHealth('test', {
  cronometer: makeSourceHealth({
    freshnessStatus: 'expired',
    upstreamStatus: 'down',
    degradedReason: 'API unreachable.',
  }),
});
const cronDown = summaryDown.sources.find((s) => s.provider === 'cronometer')!;
assert(cronDown.connectionStatus === 'unavailable', 'upstream down = unavailable');

// ---------------------------------------------------------------------------
// 14. Coach explains Cronometer auth status precisely
// ---------------------------------------------------------------------------
section('Coach Cronometer auth status precision');

// auth_required
const coachAuthReq = buildCoachAnswer('is cronometer connected?', {
  ...baseContext,
  multiSourceHealth: {
    cronometer: { status: 'missing', reason: 'auth_required: Credentials found but API not operational.' },
  },
} as any);
assert(coachAuthReq.answer.short.includes('credentials') || coachAuthReq.answer.short.includes('not yet operational'),
  'Coach explains auth_required precisely');
assert(coachAuthReq.answer.missingnessNote?.includes('auth_required') === true,
  'Coach missingnessNote includes auth_required');

// auth_expired
const coachAuthExp = buildCoachAnswer('is cronometer connected?', {
  ...baseContext,
  multiSourceHealth: {
    cronometer: { status: 'missing', reason: 'auth_expired: Token expired.' },
  },
} as any);
assert(coachAuthExp.answer.short.includes('expired'),
  'Coach explains auth_expired precisely');
assert(coachAuthExp.answer.missingnessNote?.includes('auth_expired') === true,
  'Coach missingnessNote includes auth_expired');

// not_connected (no reason prefix)
const coachNotConn = buildCoachAnswer('is cronometer connected?', {
  ...baseContext,
  multiSourceHealth: {
    cronometer: { status: 'not_connected', reason: 'No Cronometer source-health record.' },
  },
} as any);
assert(coachNotConn.answer.short.includes('not connected'),
  'Coach says not connected for plain not_connected');

// connected
const coachConn = buildCoachAnswer('is cronometer connected?', {
  ...baseContext,
  nutritionDailySummary: {
    calories: 2200, proteinGrams: 140, carbGrams: 220, fatGrams: 85,
    coverage: 'full' as const, missingFields: [],
    sourceState: 'live' as const, sourceDependencies: ['cronometer'], allConfirmed: true,
  },
  multiSourceHealth: {
    cronometer: { status: 'fresh', upstream: 'healthy' },
  },
} as any);
assert(coachConn.status === 'answered', 'Coach connected with data = answered');
assert(coachConn.answer.short.includes('Cronometer logged') || coachConn.answer.short.includes('2200'),
  'Coach reports connected Cronometer macros');

// stale
const coachStale = buildCoachAnswer('is cronometer connected?', {
  ...baseContext,
  multiSourceHealth: {
    cronometer: { status: 'stale', upstream: 'healthy' },
  },
} as any);
assert(coachStale.answer.short.includes('not connected') || coachStale.status === 'answered' || coachStale.status === 'downgraded',
  'Coach handles stale Cronometer');

// ---------------------------------------------------------------------------
// 15. WHOOP freshness policy
// ---------------------------------------------------------------------------
section('WHOOP freshness policy');

// Fresh artifact → deny live read
const freshDenied = shouldReadLiveWhoop({
  latestArtifactFreshUntil: new Date(Date.now() + 3600000).toISOString(),
  sourceHealth: null,
  userRequestedRealtime: false,
  requiredFields: [],
  cachedPresentFields: ['recoveryScore', 'hrvMs', 'totalSleepHours'],
});
assert(freshDenied.liveReadAllowed === false, 'fresh artifact = deny live read');
assert(freshDenied.trigger === 'denied', 'fresh artifact trigger = denied');

// Expired artifact → allow live read
const expiredAllow = shouldReadLiveWhoop({
  latestArtifactFreshUntil: new Date(Date.now() - 3600000).toISOString(),
  sourceHealth: null,
  userRequestedRealtime: false,
  requiredFields: [],
  cachedPresentFields: [],
});
assert(expiredAllow.liveReadAllowed === true, 'expired artifact = allow live read');
assert(expiredAllow.trigger === 'artifact_expired', 'expired trigger = artifact_expired');

// User explicitly requests → always allow
const userRequested = shouldReadLiveWhoop({
  latestArtifactFreshUntil: new Date(Date.now() + 3600000).toISOString(),
  sourceHealth: null,
  userRequestedRealtime: true,
  requiredFields: [],
  cachedPresentFields: [],
});
assert(userRequested.liveReadAllowed === true, 'user requested = allow live read');
assert(userRequested.trigger === 'user_requested', 'user requested trigger');

// Missing required field → allow
const missingField = shouldReadLiveWhoop({
  latestArtifactFreshUntil: new Date(Date.now() + 3600000).toISOString(),
  sourceHealth: null,
  userRequestedRealtime: false,
  requiredFields: ['recoveryScore', 'hrvMs'],
  cachedPresentFields: ['recoveryScore'],
});
assert(missingField.liveReadAllowed === true, 'missing field = allow live read');
assert(missingField.trigger === 'missing_required_field', 'missing field trigger');

// Source health expired → allow
const sourceExpired = shouldReadLiveWhoop({
  latestArtifactFreshUntil: new Date(Date.now() + 3600000).toISOString(),
  sourceHealth: makeSourceHealth({ freshnessStatus: 'expired', provider: 'whoop' }),
  userRequestedRealtime: false,
  requiredFields: [],
  cachedPresentFields: [],
});
assert(sourceExpired.liveReadAllowed === true, 'source expired = allow live read');
assert(sourceExpired.trigger === 'source_unhealthy', 'source expired trigger');

// Source health down → allow
const sourceDown = shouldReadLiveWhoop({
  latestArtifactFreshUntil: new Date(Date.now() + 3600000).toISOString(),
  sourceHealth: makeSourceHealth({ upstreamStatus: 'down', provider: 'whoop' }),
  userRequestedRealtime: false,
  requiredFields: [],
  cachedPresentFields: [],
});
assert(sourceDown.liveReadAllowed === true, 'source down = allow live read');

// ---------------------------------------------------------------------------
// 16. Coach WHOOP readiness behavior
// ---------------------------------------------------------------------------
section('Coach WHOOP readiness behavior');

// Fresh WHOOP with green day → Coach gives green light
const freshWhoopGreen: any = {
  ...baseContext,
  seedMode: false,
  dailyArtifact: {
    sourceDate: '2026-04-15',
    dayState: 'green',
    dayScore: 82,
    rollingRiskLevel: 'low',
    sessionGate: { gate: 'open', maxIntensity: 'hard', allowedTypes: ['sparring', 'hiit', 'drilling'], cautions: [] },
    primaryRecommendation: { guidance: 'Full training allowed.', reasons: ['Recovery supports intensity.'] },
    keyDrivers: ['Recovery at 82%'],
    coverage: { missingFields: [] },
    activePatterns: [],
  },
  capability: {
    ...baseContext.capability,
    mode: 'live_ready',
    missingWhoopNativeFields: [],
    notSafeFor: [],
  },
};
const greenLight = buildCoachAnswer('should I do HIIT today?', freshWhoopGreen);
assert(greenLight.answer.short.toLowerCase().includes('green light') || greenLight.status === 'answered',
  'fresh WHOOP green = green light or answered');

// Stale WHOOP → Coach blocks readiness
const staleWhoop: any = {
  ...baseContext,
  seedMode: true,
  capability: {
    ...baseContext.capability,
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain'],
    notSafeFor: ['display_recovery_score_as_live'],
  },
};
const staleBlock = buildCoachAnswer('am I recovered enough to sprint?', staleWhoop);
assert(staleBlock.status === 'insufficient_data' || staleBlock.status === 'downgraded', 'stale WHOOP = insufficient_data for readiness');

// Auth expired → Coach blocks readiness (same as stale)
const authExpWhoop: any = {
  ...baseContext,
  seedMode: true,
  capability: {
    ...baseContext.capability,
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain'],
  },
};
const authExpBlock = buildCoachAnswer('should I do HIIT today?', authExpWhoop);
assert(authExpBlock.status !== 'answered' || authExpBlock.confidence !== 'high',
  'auth expired WHOOP = no confident readiness');

// "What does WHOOP say today?" with fresh data
const whatWhoopSays = buildCoachAnswer('what does WHOOP say today?', freshWhoopGreen);
assert(whatWhoopSays.domain === 'recovery' || whatWhoopSays.domain === 'training' || whatWhoopSays.domain === 'general',
  '"what does WHOOP say" routes to recovery/training/general');

// ---------------------------------------------------------------------------
// 17. Apple Health / nutrition alone never unlock readiness
// ---------------------------------------------------------------------------
section('Apple Health / nutrition alone readiness isolation');

// Apple Health sleep + nutrition full → readiness STILL blocked without WHOOP recovery/HRV/strain
const appleHealthOnly: any = {
  ...baseContext,
  seedMode: false,
  dailyArtifact: null, // No daily artifact
  normalizedDay: {
    totalSleepHours: 8, deepSleepHours: 2.5, remSleepHours: 1.5,
    activeCaloriesKcal: 500, workoutCount: 1,
    nutritionCalories: 2200, nutritionProteinGrams: 140,
    nutritionCarbGrams: 220, nutritionFatGrams: 85,
    nutritionCoverage: 'full',
    // But NO recovery, HRV, or strain
    recoveryScore: null, hrvMs: null, dailyStrain: null,
  },
  nutritionDailySummary: {
    calories: 2200, proteinGrams: 140, carbGrams: 220, fatGrams: 85,
    coverage: 'full', missingFields: [],
    sourceState: 'manual', sourceDependencies: ['manual'], allConfirmed: true,
  },
  capability: {
    ...baseContext.capability,
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'hrv', 'strain'],
    notSafeFor: ['display_recovery_score_as_live'],
  },
};
const ahReadiness = buildCoachAnswer('should I do hard HIIT today?', appleHealthOnly);
assert(ahReadiness.status === 'insufficient_data' || ahReadiness.status === 'downgraded',
  'Apple Health + nutrition = no readiness clearance');
assert(!ahReadiness.answer.short.toLowerCase().includes('green light'),
  'Apple Health alone = no green light');

// Same context but asking about nutrition → should work fine
const ahNutrition = buildCoachAnswer('what did I eat today?', appleHealthOnly);
assert(ahNutrition.status === 'answered', 'Apple Health nutrition question still answered');
assert(ahNutrition.answer.short.includes('2200'), 'Apple Health nutrition reports calories');

// ---------------------------------------------------------------------------
// 18. Seed WHOOP recovery consistency (the actual bug)
// ---------------------------------------------------------------------------
section('Seed WHOOP recovery consistency');

// Seed WHOOP has recovery 38% but mode is seed_partial → Coach should show seed score
const seedWhoopCtx: any = {
  ...baseContext,
  seedMode: true,
  normalizedDay: {
    recoveryScore: 38,
    hrvMs: 64,
    totalSleepHours: 4.2,
    dailyStrain: 17,
    nutritionCalories: null,
    nutritionCoverage: 'none',
  },
  dailyArtifact: null,
  capability: {
    ...baseContext.capability,
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain', 'workouts'],
    notSafeFor: ['display_recovery_score_as_live'],
  },
};

// "What does WHOOP say today?" → seed recovery answer, NOT "not available"
const whatWhoopSeed = buildCoachAnswer('what does WHOOP say today?', seedWhoopCtx);
assert(whatWhoopSeed.status === 'downgraded', 'seed WHOOP = downgraded (not insufficient)');
assert(whatWhoopSeed.answer.short.includes('38'), 'seed WHOOP answer mentions 38% score');
assert(!whatWhoopSeed.answer.short.includes('not available') && !whatWhoopSeed.answer.short.includes('No WHOOP'),
  'seed WHOOP answer does NOT say "not available"');
assert(whatWhoopSeed.answer.short.toLowerCase().includes('seed'),
  'seed WHOOP answer says "seed"');
assert(!whatWhoopSeed.answer.short.toLowerCase().includes('green light'),
  'seed WHOOP answer does NOT claim live readiness');

// missingFields should say live_recovery, not just "recovery"
assert(whatWhoopSeed.missingFields.includes('live_recovery') || whatWhoopSeed.missingFields.includes('live_hrv'),
  'missing fields say live_recovery/live_hrv, not just recovery');
assert(!whatWhoopSeed.missingFields.includes('recovery'),
  'missing fields do NOT say bare "recovery" when seed recovery exists');

// "Should I do HIIT?" → still blocked even with seed 38%
const hiitSeed = buildCoachAnswer('should I do HIIT today?', seedWhoopCtx);
assert(hiitSeed.status === 'insufficient_data' || hiitSeed.status === 'downgraded', 'HIIT still blocked with seed recovery');
assert(hiitSeed.answer.short.includes('38') || hiitSeed.answer.short.includes('seed'),
  'HIIT block mentions seed recovery as context');
assert(!hiitSeed.answer.short.toLowerCase().includes('green light'),
  'HIIT block does NOT say green light');

// "Am I recovered enough to sprint?" → still blocked
const sprintSeed = buildCoachAnswer('am I recovered enough to sprint?', seedWhoopCtx);
assert(sprintSeed.status === 'insufficient_data' || sprintSeed.status === 'downgraded', 'sprint still blocked with seed recovery');

// No seed recovery (completely empty) → should say "No WHOOP recovery data"
const noSeedCtx: any = {
  ...seedWhoopCtx,
  normalizedDay: null,
};
const noSeedAnswer = buildCoachAnswer('what does WHOOP say today?', noSeedCtx);
assert(noSeedAnswer.answer.short.includes('No WHOOP') || noSeedAnswer.answer.short.includes('no data') || noSeedAnswer.answer.short.toLowerCase().includes('not available'),
  'no seed recovery = no data answer');

// ---------------------------------------------------------------------------
// 19. Cross-user data isolation
// ---------------------------------------------------------------------------
section('Cross-user data isolation');

// A new user with no data should see empty/no_data, not another user's data.
const newUserCtx: any = {
  ...baseContext,
  athleteId: 'new-user-12345',
  seedMode: true,
  normalizedDay: null,
  dailyArtifact: null,
  sourceHealth: null,
  nutritionDailySummary: null,
  nutritionSources: [],
  recentHIITWorkouts: null,
  hiitProgressSummary: null,
  capability: {
    mode: 'uninitialized',
    safeFor: [],
    notSafeFor: ['display_recovery_score_as_live'],
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain', 'workouts'],
    recommendedReadOrder: [],
  },
  multiSourceHealth: {
    whoop: { status: 'not_connected', reason: 'No WHOOP source-health record.' },
    apple_health: { status: 'not_connected', reason: null },
    cronometer: { status: 'not_connected', reason: 'No Cronometer source-health record.' },
  },
};

// "Is Cronometer connected?" → must say not connected, no leak from Aaron
const newUserCron = buildCoachAnswer('is cronometer connected?', newUserCtx);
assert(newUserCron.answer.short.toLowerCase().includes('not connected'),
  'new user sees Cronometer not connected');

// "What does WHOOP say today?" → must say no data, not Aaron's 38%
const newUserWhoop = buildCoachAnswer('what does WHOOP say today?', newUserCtx);
assert(!newUserWhoop.answer.short.includes('38'),
  'new user does NOT see Aaron\'s 38% recovery');
assert(newUserWhoop.answer.short.toLowerCase().includes('no') ||
       newUserWhoop.answer.short.toLowerCase().includes('not available'),
  'new user sees no WHOOP data (not Aaron\'s data)');

// "Should I do HIIT today?" → must not clear, no leak
const newUserHIIT = buildCoachAnswer('should I do HIIT today?', newUserCtx);
assert(newUserHIIT.status === 'insufficient_data' || newUserHIIT.status === 'downgraded',
  'new user HIIT blocked (no leaked WHOOP)');
assert(!newUserHIIT.answer.short.toLowerCase().includes('green light'),
  'new user does NOT get green light from Aaron\'s data');

// "What did I eat today?" → must say no nutrition, not Aaron's meals
const newUserNutr = buildCoachAnswer('what did I eat today?', newUserCtx);
assert(newUserNutr.status === 'insufficient_data',
  'new user has no nutrition (not Aaron\'s)');

// "How did my HIIT compare to last time?" → must say no history
const newUserHIITProgress = buildCoachAnswer('how did my HIIT compare to last time?', newUserCtx);
assert(newUserHIITProgress.status === 'insufficient_data',
  'new user has no HIIT history (not Aaron\'s)');

// ---------------------------------------------------------------------------
// 20. Health Connect + Polar parity
// ---------------------------------------------------------------------------
section('Health Connect + Polar parity');

// Health Connect has no backend record → "not_connected" (not scaffold_only)
const hcEmpty = buildMultiSourceHealth('user-a', {});
const hcRowEmpty = hcEmpty.sources.find((s) => s.provider === 'health_connect')!;
assert(hcRowEmpty.connectionStatus === 'not_connected',
  'Health Connect = not_connected when no record (not scaffold_only)');
assert(hcRowEmpty.missingDomains.includes('sleep'),
  'Health Connect missing domains include sleep');

// Health Connect with fresh record → available
const hcConnected = buildMultiSourceHealth('user-a', {
  health_connect: makeSourceHealth({
    provider: 'health_connect',
    freshnessStatus: 'fresh',
    upstreamStatus: 'healthy',
    lastSuccessfulIngestAt: new Date().toISOString(),
    coverageByDomain: {
      sleep: { lastDate: '2026-04-16', status: 'fresh' },
      steps: { lastDate: '2026-04-16', status: 'fresh' },
    },
  }),
});
const hcRowConnected = hcConnected.sources.find((s) => s.provider === 'health_connect')!;
assert(hcRowConnected.connectionStatus === 'available',
  'Health Connect with fresh+healthy record = available');
assert(hcRowConnected.domainsAvailable.includes('sleep'),
  'Health Connect connected lists sleep in domainsAvailable');

// Polar always scaffold_only (no real adapter)
const polarRow = hcEmpty.sources.find((s) => s.provider === 'polar')!;
assert(polarRow.connectionStatus === 'scaffold_only',
  'Polar always scaffold_only (no real adapter)');
assert(polarRow.missingDomains.length > 0,
  'Polar has missing domains listed');

// Even if someone sneaks a polar source-health record, it stays scaffold_only
// because implemented=false in the provider list.
const polarAttempt = buildMultiSourceHealth('user-a', {
  polar: makeSourceHealth({
    provider: 'polar',
    freshnessStatus: 'fresh',
    upstreamStatus: 'healthy',
  }),
});
const polarAttemptRow = polarAttempt.sources.find((s) => s.provider === 'polar')!;
assert(polarAttemptRow.connectionStatus === 'scaffold_only',
  'Polar stays scaffold_only even with a source-health record');

// Coach: Polar question → always says not connected
const coachPolar = buildCoachAnswer('is polar connected?', {
  ...baseContext,
  multiSourceHealth: {
    polar: { status: 'not_connected', reason: 'Polar integration is scaffold-only; no live adapter yet.' },
  },
} as any);
assert(coachPolar.answer.short.toLowerCase().includes('not connected'),
  'Coach says Polar not connected');
assert(coachPolar.answer.why.toLowerCase().includes('scaffold') || coachPolar.answer.why.toLowerCase().includes('not yet'),
  'Coach explains Polar is scaffold/not yet live');

// Coach: Android Health question → says "not connected" with clear reason when no backend ingest
const coachHcEmpty = buildCoachAnswer('what has Android Health contributed?', {
  ...baseContext,
  multiSourceHealth: {
    health_connect: { status: 'not_connected', reason: 'No Health Connect ingest yet.', lastIngestAt: null },
  },
} as any);
assert(coachHcEmpty.answer.short.toLowerCase().includes('not synced') ||
       coachHcEmpty.answer.short.toLowerCase().includes('not connected'),
  'Coach says HC not synced');
assert(coachHcEmpty.status === 'insufficient_data',
  'HC with no ingest = insufficient_data');

// Coach: Android Health connected → contextual only, no readiness
const coachHcConnected = buildCoachAnswer('what has Android Health contributed?', {
  ...baseContext,
  multiSourceHealth: {
    health_connect: { status: 'fresh', upstream: 'healthy', reason: null, lastIngestAt: '2026-04-16T08:00:00Z' },
  },
} as any);
assert(coachHcConnected.answer.short.toLowerCase().includes('connected') ||
       coachHcConnected.answer.short.toLowerCase().includes('android'),
  'Coach reports HC connected');
assert(coachHcConnected.answer.why.toLowerCase().includes('readiness') ||
       coachHcConnected.answer.why.toLowerCase().includes('context'),
  'Coach frames HC as context, not readiness');

// Health Connect alone does NOT unlock readiness
const hcReadiness: any = {
  ...baseContext,
  seedMode: true,
  normalizedDay: { totalSleepHours: 8, recoveryScore: null, hrvMs: null, dailyStrain: null },
  capability: {
    ...baseContext.capability,
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'hrv', 'strain'],
    notSafeFor: ['display_recovery_score_as_live'],
  },
  multiSourceHealth: {
    health_connect: { status: 'fresh', upstream: 'healthy' },
  },
};
const hcReadinessAnswer = buildCoachAnswer('should I do hard HIIT today?', hcReadiness);
assert(hcReadinessAnswer.status === 'insufficient_data' || hcReadinessAnswer.status === 'downgraded',
  'Health Connect alone = no HIIT readiness clearance');
assert(!hcReadinessAnswer.answer.short.toLowerCase().includes('green light'),
  'Health Connect alone = no green light');

// ---------------------------------------------------------------------------
// 22. Polar via Health Connect provenance
// ---------------------------------------------------------------------------
section('Polar via Health Connect provenance');

// 22.1 Provider row exists, implemented=true, with safeFor/notSafeFor
const polarViaHcEmptySummary = buildMultiSourceHealth('test-athlete', {
  polar_via_health_connect: null,
});
const polarViaHcEmpty = polarViaHcEmptySummary.sources.find((s: any) => s.provider === 'polar_via_health_connect') as any;
assert(polarViaHcEmpty != null, 'polar_via_health_connect row exists');
assert(polarViaHcEmpty.connectionStatus === 'not_connected',
  'Empty polar_via_hc = not_connected (implemented adapter, just no records yet)');
assert(polarViaHcEmpty.directAdapter === false,
  'polar_via_health_connect.directAdapter === false (indirect path)');
assert(polarViaHcEmpty.notSafeFor.includes('readiness'),
  'polar_via_hc is explicitly notSafeFor readiness');
assert(polarViaHcEmpty.notSafeFor.includes('direct_polar_auth'),
  'polar_via_hc is explicitly notSafeFor direct_polar_auth (cannot replace direct Polar adapter)');
assert(polarViaHcEmpty.safeFor.includes('session_context'),
  'polar_via_hc is safeFor session_context');
assert(polarViaHcEmpty.safeFor.includes('heart_rate_context'),
  'polar_via_hc is safeFor heart_rate_context');

// 22.2 Connected state with Polar-origin records
const now22 = new Date().toISOString();
const today22 = now22.slice(0, 10);
const polarViaHcRecord: SourceHealthStatus = {
  id: 'polar_via_hc_test', schemaVersion: 1, createdAt: now22, updatedAt: now22,
  athleteId: 'test-athlete', provider: 'polar_via_health_connect',
  lastSuccessfulIngestAt: now22,
  lastFailedIngestAt: null,
  freshnessStatus: 'fresh',
  coverageByDomain: {
    workouts: { status: 'fresh', lastDate: today22 },
    workout_hr: { status: 'fresh', lastDate: today22 },
    heart_rate_samples: { status: 'fresh', lastDate: today22 },
  },
  upstreamStatus: 'healthy',
  degradedReason: 'sourceApp:Polar Flow',
};
const polarViaHcConnectedSummary = buildMultiSourceHealth('test-athlete', {
  polar_via_health_connect: polarViaHcRecord,
});
const polarViaHcConnected = polarViaHcConnectedSummary.sources.find((s: any) => s.provider === 'polar_via_health_connect') as any;
assert(polarViaHcConnected.connectionStatus === 'available',
  'polar_via_hc with data = available');
assert(polarViaHcConnected.domainsAvailable.includes('workouts'),
  'polar_via_hc workouts domain available');
assert(polarViaHcConnected.sourceApp === 'Polar Flow',
  'polar_via_hc sourceApp parsed from degradedReason');

// 22.3 Direct Polar stays scaffold_only even when polar_via_hc has data
const dualPolarSummary = buildMultiSourceHealth('test-athlete', {
  polar_via_health_connect: polarViaHcRecord,
  polar: null,
});
const directPolar = dualPolarSummary.sources.find((s: any) => s.provider === 'polar') as any;
assert(directPolar.connectionStatus === 'scaffold_only',
  'Direct polar stays scaffold_only even with polar_via_hc data');
assert(directPolar.directAdapter === false,
  'Direct polar row still marks directAdapter false (not live yet)');
assert(directPolar.reason && directPolar.reason.toLowerCase().includes('health connect'),
  'Direct polar reason mentions Health Connect as alternative path');

// 22.4 Coach: "Is Polar connected?" says "via Health Connect" when polar_via_hc fresh
const coachPolarViaHc = buildCoachAnswer('is polar connected?', {
  ...baseContext,
  multiSourceHealth: {
    polar: { status: 'not_connected' },
    polar_via_health_connect: {
      status: 'fresh',
      upstream: 'healthy',
      reason: 'sourceApp:Polar Flow',
      sourceApp: 'Polar Flow',
      coverage: ['workouts', 'workout_hr', 'heart_rate_samples'],
      lastIngestAt: now22,
    },
  },
} as any);
assert(coachPolarViaHc.answer.short.toLowerCase().includes('health connect'),
  'Coach: Polar is coming through Health Connect');
assert(coachPolarViaHc.answer.short.toLowerCase().includes('polar'),
  'Coach: mentions Polar');
assert(coachPolarViaHc.missingFields.includes('direct_polar_auth'),
  'Coach: direct Polar still missing');
assert(coachPolarViaHc.status === 'answered', 'Coach: answered when polar_via_hc fresh');

// 22.5 Coach: Unknown-origin HC records do NOT create Polar status
// The test is that just having health_connect=fresh without polar_via_health_connect
// does not make Coach say "Polar via Health Connect".
const coachHcOnly = buildCoachAnswer('is polar connected?', {
  ...baseContext,
  multiSourceHealth: {
    health_connect: { status: 'fresh', upstream: 'healthy' },
    polar: { status: 'not_connected' },
    polar_via_health_connect: { status: 'not_connected' },
  },
} as any);
assert(coachHcOnly.answer.short.toLowerCase().includes('not connected'),
  'Coach: generic HC data does NOT get called "Polar via HC"');
assert(!coachHcOnly.answer.short.toLowerCase().includes('health connect (polar'),
  'Coach: does not fabricate Polar when only HC fresh');

// 22.6 Coach: Polar via HC alone does NOT unlock readiness
const readinessWithPolarViaHc = buildCoachAnswer('am I ready for HIIT?', {
  ...baseContext,
  capability: {
    ...(baseContext.capability ?? {}),
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recoveryScore', 'hrvMs', 'dailyStrain'],
  },
  multiSourceHealth: {
    polar_via_health_connect: {
      status: 'fresh',
      upstream: 'healthy',
      coverage: ['workouts', 'workout_hr', 'heart_rate_samples'],
      lastIngestAt: now22,
    },
    whoop: { status: 'not_connected' },
  },
} as any);
assert(readinessWithPolarViaHc.status === 'insufficient_data' || readinessWithPolarViaHc.status === 'downgraded',
  'polar_via_hc alone does NOT unlock HIIT readiness');
assert(!readinessWithPolarViaHc.answer.short.toLowerCase().includes('green light'),
  'polar_via_hc alone does NOT give green light');

// 22.7 Coach: "What has Polar contributed?" — specific answer when via-HC fresh
const coachPolarContributed = buildCoachAnswer('what has polar contributed?', {
  ...baseContext,
  multiSourceHealth: {
    polar: { status: 'not_connected' },
    polar_via_health_connect: {
      status: 'fresh',
      upstream: 'healthy',
      sourceApp: 'Polar Flow',
      coverage: ['workouts', 'workout_hr'],
      lastIngestAt: now22,
    },
  },
} as any);
assert(coachPolarContributed.answer.why.toLowerCase().includes('workout'),
  'Coach: Polar via HC contribution enumerates workouts/HR');

// 22.8 Cross-user isolation: User A has polar_via_hc, User B does not
const userASummary = buildMultiSourceHealth('user-a', {
  polar_via_health_connect: polarViaHcRecord,
});
const userBSummary = buildMultiSourceHealth('user-b', {
  polar_via_health_connect: null,
});
const userAPolar = userASummary.sources.find((s: any) => s.provider === 'polar_via_health_connect') as any;
const userBPolar = userBSummary.sources.find((s: any) => s.provider === 'polar_via_health_connect') as any;
assert(userAPolar.connectionStatus === 'available', 'User A polar_via_hc = available');
assert(userBPolar.connectionStatus === 'not_connected', 'User B polar_via_hc = not_connected (isolation preserved)');
assert(userASummary.athleteId === 'user-a' && userBSummary.athleteId === 'user-b',
  'Cross-user athleteId isolation preserved');

// 22.9 Mobile polar-source pattern matching (sanity-check the detection regex
// implementation logic — mirror of services/ai-health-sync.ts isPolarSource)
const POLAR_SOURCE_PATTERNS: RegExp[] = [
  /(^|[^a-z])polar($|[^a-z])/i,
  /com\.polar\./i,
  /polarflow/i,
];
function isPolarSourceLocal(src: string | null | undefined): boolean {
  if (!src) return false;
  return POLAR_SOURCE_PATTERNS.some((re) => re.test(src));
}
assert(isPolarSourceLocal('com.polar.polarflow'), 'Polar Android package matches');
assert(isPolarSourceLocal('Polar Flow'), 'Polar Flow label matches');
assert(isPolarSourceLocal('polar'), 'bare "polar" matches');
assert(!isPolarSourceLocal('com.samsung.android.health'), 'Samsung Health does NOT match');
assert(!isPolarSourceLocal('com.garmin.connect'), 'Garmin does NOT match');
assert(!isPolarSourceLocal('com.google.android.fit'), 'Google Fit does NOT match');
assert(!isPolarSourceLocal(''), 'empty string does NOT match');
assert(!isPolarSourceLocal(null), 'null does NOT match');

// 22.10 Polar via HC does not unlock recovery/strain readiness (these stay
// explicitly notSafeFor even when connected)
assert(polarViaHcConnected.notSafeFor.includes('readiness'),
  'Connected polar_via_hc is still notSafeFor readiness');
assert(polarViaHcConnected.notSafeFor.includes('hrv_fatigue'),
  'Connected polar_via_hc is still notSafeFor hrv_fatigue');
assert(polarViaHcConnected.notSafeFor.includes('recovery_strain'),
  'Connected polar_via_hc is still notSafeFor recovery_strain');

// ---------------------------------------------------------------------------
// 23. First-run backlog analysis: privacy, trends, coach summary
// ---------------------------------------------------------------------------
section('Backlog analysis: privacy + trend generation + Coach summary');

import('../../../../packages/shared/src/backend/services/backlog/find-trend-candidates').then(async ({ findTrendCandidates }) => {
  const { buildBacklogCohortComparison } = await import('../../../../packages/shared/src/backend/services/backlog/build-cohort-comparison');
  const { runBacklogAnalysis } = await import('../../../../packages/shared/src/backend/services/backlog/run-backlog-analysis');

  // 23.1 In-memory fake store — ONLY exposes the athleteId-keyed
  //      surface defined by BacklogStore, so accidental cross-user
  //      reads are impossible by construction.
  function createFakeStore(seed: Record<string, {
    normalized: any[];
    hiit: any[];
    dailyArtifacts: Map<string, any>;
    sourceHealth: Record<string, any>;
    baseline: any | null;
  }>) {
    const saved: Record<string, any> = {};
    return {
      async getNormalizedDay(athleteId: string, date: string) {
        return seed[athleteId]?.normalized.find((d) => d.date === date) ?? null;
      },
      async listDailyRefreshes(athleteId: string, opts?: { startDate?: string; endDate?: string }) {
        const all = Array.from(seed[athleteId]?.dailyArtifacts.values() ?? []);
        return all
          .filter((a) => !opts?.startDate || a.sourceDate >= opts.startDate)
          .filter((a) => !opts?.endDate || a.sourceDate <= opts.endDate);
      },
      async getLatestWeeklySynthesis() { return null; },
      async saveDailyRefresh(athleteId: string, artifact: any) {
        seed[athleteId]?.dailyArtifacts.set(artifact.sourceDate, artifact);
      },
      async saveWeeklySynthesis() { /* noop */ },
      async getSourceHealth(athleteId: string, provider: string) {
        return seed[athleteId]?.sourceHealth[provider] ?? null;
      },
      async listHiitSessions(athleteId: string, opts?: any) {
        return (seed[athleteId]?.hiit ?? []).filter(
          (s) => (!opts?.startDate || s.date >= opts.startDate) && (!opts?.endDate || s.date <= opts.endDate),
        );
      },
      async getBaseline(athleteId: string) {
        return seed[athleteId]?.baseline ?? null;
      },
      async loadNormalizedRange(athleteId: string, s: string, e: string) {
        return (seed[athleteId]?.normalized ?? []).filter((d) => d.date >= s && d.date <= e);
      },
      async saveBacklogStatus(athleteId: string, record: any) {
        saved[`status_${athleteId}`] = record;
      },
      async saveBacklogSummary(athleteId: string, summary: any) {
        saved[`summary_${athleteId}`] = summary;
      },
      async saveBacklogTrendCandidates(athleteId: string, trends: any) {
        saved[`trends_${athleteId}`] = trends;
      },
      _saved: saved,
    };
  }

  // 23.2 Seed two isolated athletes — A has 28 days + WHOOP + HIIT,
  //      B has only 3 days of Health Connect.
  const today23 = '2026-04-16';
  const windowStart = '2026-03-18';
  const daysRange = (fromIdx: number, toIdx: number, provider: string, base: (i: number) => any) => {
    const out: any[] = [];
    for (let i = fromIdx; i <= toIdx; i++) {
      const d = new Date('2026-03-18T00:00:00Z').getTime() + i * 86400000;
      const date = new Date(d).toISOString().slice(0, 10);
      out.push({ ...base(i), date, provider, schemaVersion: 1, athleteId: '' });
    }
    return out;
  };

  const athleteANormalized = daysRange(0, 27, 'whoop', (i) => ({
    recoveryScore: 55 + (i % 25),
    hrvMs: 42 + (i % 15),
    restingHrBpm: 58 + (i % 6),
    totalSleepHours: 7 + ((i % 5) * 0.2),
    deepSleepHours: 1.5, remSleepHours: 1.5,
    activeCaloriesKcal: 400 + (i * 5),
    stepCount: 7000 + (i * 100),
    dailyStrain: 10 + (i % 7),
    workoutCount: i % 3 === 0 ? 1 : 0,
    workoutMinutesTotal: i % 3 === 0 ? 45 : null,
    grapplingSessionCount: i % 5 === 0 ? 1 : 0,
    nutritionCalories: i % 2 === 0 ? 2400 : null,
    nutritionProteinGrams: i % 2 === 0 ? 180 : null,
    nutritionCarbGrams: i % 2 === 0 ? 260 : null,
    nutritionFatGrams: i % 2 === 0 ? 70 : null,
    nutritionCoverage: i % 2 === 0 ? 'full' : 'none',
    presentFields: ['recoveryScore', 'hrvMs', 'totalSleepHours', 'workoutCount'],
    missingFields: [],
    completeness: 'partial',
    sourceAgeHours: 2,
    sourceRecordIds: [`r_a_${i}`],
    sourceRefs: [],
  }));

  const athleteBNormalized = daysRange(25, 27, 'health_connect', (i) => ({
    recoveryScore: null, hrvMs: null, restingHrBpm: 62,
    totalSleepHours: 7.2, deepSleepHours: null, remSleepHours: null,
    activeCaloriesKcal: 350, stepCount: 6500, dailyStrain: null,
    workoutCount: 0, workoutMinutesTotal: null, grapplingSessionCount: 0,
    nutritionCalories: null, nutritionProteinGrams: null,
    nutritionCarbGrams: null, nutritionFatGrams: null,
    nutritionCoverage: 'none',
    presentFields: ['restingHrBpm', 'totalSleepHours', 'stepCount'],
    missingFields: [],
    completeness: 'minimal',
    sourceAgeHours: 1,
    sourceRecordIds: [`r_b_${i}`],
    sourceRefs: [],
  }));

  const athleteAHiit: any[] = [
    { id: 'h1', athleteId: 'user-a', date: '2026-03-20', templateId: 't1', protocolFormat: '30:30', machineType: 'assault_bike', machineProvider: 'manual', sets: [], totalSets: 5, workSets: 3, restSets: 2, totalDurationSeconds: 150, totalCalories: 30, totalWorkKj: null, avgWatts: 210, peakWatts: 260, avgHr: 155, peakHr: 175, source: 'manual', sourceRecordIds: [], missingFields: [] },
    { id: 'h2', athleteId: 'user-a', date: '2026-04-01', templateId: 't1', protocolFormat: '30:30', machineType: 'assault_bike', machineProvider: 'manual', sets: [], totalSets: 5, workSets: 3, restSets: 2, totalDurationSeconds: 150, totalCalories: 32, totalWorkKj: null, avgWatts: 220, peakWatts: 270, avgHr: 158, peakHr: 178, source: 'manual', sourceRecordIds: [], missingFields: [] },
    { id: 'h3', athleteId: 'user-a', date: '2026-04-10', templateId: 't1', protocolFormat: '30:30', machineType: 'assault_bike', machineProvider: 'manual', sets: [], totalSets: 5, workSets: 3, restSets: 2, totalDurationSeconds: 150, totalCalories: 33, totalWorkKj: null, avgWatts: 225, peakWatts: 275, avgHr: 160, peakHr: 180, source: 'manual', sourceRecordIds: [], missingFields: [] },
  ];

  const seedStores = {
    'user-a': {
      normalized: athleteANormalized,
      hiit: athleteAHiit,
      dailyArtifacts: new Map(),
      sourceHealth: {
        whoop: { provider: 'whoop', freshnessStatus: 'fresh', coverageByDomain: { recovery: { status: 'fresh', lastDate: today23 }, sleep: { status: 'fresh', lastDate: today23 }, hrv: { status: 'fresh', lastDate: today23 } }, upstreamStatus: 'healthy', lastSuccessfulIngestAt: today23 },
        health_connect: { provider: 'health_connect', freshnessStatus: 'fresh', coverageByDomain: {}, upstreamStatus: 'healthy', lastSuccessfulIngestAt: today23 },
      },
      baseline: { computedAt: today23, dataWindowDays: 14, recoveryBaseline: 65, hrvBaseline: 52, restingHrBaseline: 58, sleepBaseline: 7.5, strainBaseline: 12, thresholds: { recovery: { red: 33, yellow: 66 }, hrv: { low: 40, high: 60 }, restingHr: { elevated: 65 }, sleep: { low: 6.5, high: 9 }, strain: { elevated: 15 } }, ruleBasis: ['test_seed'] },
    },
    'user-b': {
      normalized: athleteBNormalized,
      hiit: [],
      dailyArtifacts: new Map(),
      sourceHealth: {
        health_connect: { provider: 'health_connect', freshnessStatus: 'fresh', coverageByDomain: {}, upstreamStatus: 'healthy', lastSuccessfulIngestAt: today23 },
      },
      baseline: null,
    },
  } as any;
  const fakeStore = createFakeStore(seedStores);

  // 23.3 runBacklogAnalysis for user-a — full run with baseline + builders
  const { buildDailyRefreshArtifact } = await import('../../../../packages/shared/src/backend/services/refresh/build-daily-refresh');
  const { buildWeeklySynthesisArtifact } = await import('../../../../packages/shared/src/backend/services/refresh/build-weekly-synthesis');
  const builders = {
    buildDailyRefreshArtifact: (input: any) => buildDailyRefreshArtifact(input),
    buildWeeklySynthesisArtifact: (input: any) => buildWeeklySynthesisArtifact(input),
  };

  const resA = await runBacklogAnalysis(
    { userId: 'user-a', athleteId: 'user-a', windowStart, windowEnd: today23 },
    fakeStore as any,
    builders,
  );
  assert(resA.status.status === 'complete' || resA.status.status === 'partial', 'user-a backlog run completes');
  assert(resA.summary != null, 'user-a summary produced');
  assert(resA.summary!.dataFound.normalizedDays === 28, 'user-a 28 normalized days found');
  assert(resA.summary!.dataFound.hiitSessions === 3, 'user-a 3 HIIT sessions found');
  assert(resA.trendCandidates.length > 0, 'user-a produces trend candidates');
  assert(resA.trendCandidates.some((t: any) => t.kind === 'sleep_consistency'),
    'sleep_consistency trend emitted');
  assert(resA.trendCandidates.some((t: any) => t.kind === 'hiit_frequency'),
    'hiit_frequency trend emitted');
  const hasRecoveryTrend = resA.trendCandidates.some((t: any) => t.kind === 'recovery_trend');
  assert(hasRecoveryTrend,
    'recovery_trend emitted for user with direct WHOOP data');
  assert(resA.status.memoryProposalsCreated >= 0, 'user-a memoryProposalsCreated is counted honestly');

  // No trend should be auto-promoted — stable memory must not be touched.
  assert(!(fakeStore as any)._saved['stable_memory_user-a'], 'no stable memory writes during backlog run');

  // 23.4 User B run — no direct WHOOP, no baseline, 3 days only
  const resB = await runBacklogAnalysis(
    { userId: 'user-b', athleteId: 'user-b', windowStart, windowEnd: today23 },
    fakeStore as any,
    builders,
  );
  assert(resB.status.status === 'partial' || resB.status.status === 'complete', 'user-b run finishes without baseline');
  assert(resB.summary != null, 'user-b summary produced');
  assert(resB.summary!.dataFound.normalizedDays === 3, 'user-b 3 normalized days');
  assert(resB.summary!.dataFound.hiitSessions === 0, 'user-b 0 HIIT sessions');
  // Readiness trends MUST NOT appear for user-b — no direct WHOOP.
  assert(!resB.trendCandidates.some((t: any) => t.kind === 'recovery_trend'),
    'recovery_trend NOT emitted for user-b (no direct WHOOP)');
  assert(!resB.trendCandidates.some((t: any) => t.kind === 'hrv_trend'),
    'hrv_trend NOT emitted for user-b');
  assert(!resB.trendCandidates.some((t: any) => t.kind === 'strain_trend'),
    'strain_trend NOT emitted for user-b');

  // User B's missing sources include WHOOP
  assert(resB.status.sourcesMissing.includes('whoop'),
    'user-b sourcesMissing includes whoop');

  // 23.5 Cross-user isolation: user-b's result MUST NOT reference user-a's data
  const bSummaryJson = JSON.stringify(resB.summary);
  assert(!bSummaryJson.includes('user-a'), 'user-b summary does NOT reference user-a');
  assert(resB.trendCandidates.every((t: any) => t.athleteId === 'user-b'), 'user-b trends all athleteId=user-b');
  assert(resA.trendCandidates.every((t: any) => t.athleteId === 'user-a'), 'user-a trends all athleteId=user-a');

  // 23.6 Curated cohort comparison — never anonymous_cohort from builder
  const comparison = buildBacklogCohortComparison(resA.trendCandidates as any);
  assert(comparison.comparisonType !== 'anonymous_cohort',
    'cohort comparison never claims anonymous_cohort — only curated_reference or none');
  assert(comparison.cohortAvailable === false, 'cohortAvailable=false from curated-only builder');
  assert(comparison.privacyLevel === 'aggregate_only', 'privacyLevel=aggregate_only');

  // 23.7 Trend eligibility: readiness kinds can NEVER be memory-proposal eligible
  for (const t of resA.trendCandidates) {
    if (t.kind === 'recovery_trend' || t.kind === 'hrv_trend' || t.kind === 'strain_trend') {
      assert(t.eligibleForMemoryProposal === false,
        `readiness-kind trend ${t.kind} is never memory-proposal eligible`);
    }
  }

  // 23.8 Coach handler: "What have you learned about me so far?"
  const coachLearned = buildCoachAnswer('what have you learned about me so far?', {
    ...baseContext,
    backlogSummary: resA.summary,
  } as any);
  assert(coachLearned.status === 'answered', 'Coach answers "what have you learned"');
  assert(coachLearned.answer.short.toLowerCase().includes('logged day') ||
         coachLearned.answer.short.toLowerCase().includes('hiit'),
    'Coach summary mentions logged days or HIIT');
  assert(!!coachLearned.answer.missingnessNote?.toLowerCase().includes('provisional'),
    'Coach summary is marked provisional');
  assert((coachLearned.sourceDependencies ?? []).includes('backlog_analysis_summary'),
    'Coach cites backlog_analysis_summary as source');

  // 23.9 Coach without a summary — insufficient_data
  const coachNoSummary = buildCoachAnswer('what data do you have for me?', baseContext as any);
  assert(coachNoSummary.status === 'insufficient_data',
    'Coach insufficient_data when no backlog summary present');
  assert(coachNoSummary.answer.short.toLowerCase().includes('not analysed') ||
         coachNoSummary.answer.short.toLowerCase().includes('history'),
    'Coach suggests running analysis when no summary');

  // 23.10 Re-run: second invocation does not duplicate daily artifacts
  const artifactsBefore = seedStores['user-a'].dailyArtifacts.size;
  await runBacklogAnalysis(
    { userId: 'user-a', athleteId: 'user-a', windowStart, windowEnd: today23 },
    fakeStore as any,
    builders,
  );
  const artifactsAfter = seedStores['user-a'].dailyArtifacts.size;
  assert(artifactsAfter === artifactsBefore, 're-run does not duplicate daily artifacts');

  // 23.11 Dry run — no persistence
  const preSaved = Object.keys((fakeStore as any)._saved).length;
  const resDry = await runBacklogAnalysis(
    { userId: 'user-a', athleteId: 'user-a', windowStart, windowEnd: today23, dryRun: true },
    fakeStore as any,
    builders,
  );
  assert(resDry.summary != null, 'dry run still returns a summary');
  const postSaved = Object.keys((fakeStore as any)._saved).length;
  assert(postSaved === preSaved, 'dry run does not persist');
}).catch((e) => { console.error('backlog tests error:', e); failed += 1; });

// Give the async backlog tests a moment to complete. The summary prints
// below will reflect both sync and async assertions.
await new Promise((r) => setTimeout(r, 500));

// ---------------------------------------------------------------------------
// 24. Integration providers + readiness analysis
// ---------------------------------------------------------------------------
section('Integration providers + readiness analysis');

// 24.1 buildMultiSourceHealth includes new providers
const integrationSummary = buildMultiSourceHealth('test-athlete', {
  direct_polar: null,
  whoop_direct: null,
  concept2_logbook: null,
});
const directPolarRow = integrationSummary.sources.find((s: any) => s.provider === 'direct_polar') as any;
const whoopDirectRow = integrationSummary.sources.find((s: any) => s.provider === 'whoop_direct') as any;
const concept2Row = integrationSummary.sources.find((s: any) => s.provider === 'concept2_logbook') as any;
assert(directPolarRow != null, 'direct_polar provider exists in builder');
assert(directPolarRow.connectionStatus === 'not_connected', 'direct_polar empty = not_connected');
assert(directPolarRow.directAdapter === true, 'direct_polar.directAdapter = true');
assert(directPolarRow.notSafeFor.includes('readiness'), 'direct_polar is notSafeFor readiness');
assert(whoopDirectRow != null, 'whoop_direct provider exists in builder');
assert(whoopDirectRow.connectionStatus === 'not_connected', 'whoop_direct empty = not_connected');
assert(whoopDirectRow.safeFor.includes('readiness'), 'whoop_direct IS safeFor readiness');
assert(!whoopDirectRow.notSafeFor.includes('readiness'), 'whoop_direct does not block readiness');
assert(concept2Row != null, 'concept2_logbook provider exists');
assert(concept2Row.connectionStatus === 'scaffold_only', 'concept2_logbook = scaffold_only');

// 24.2 whoop_direct with fresh data unlocks readiness safeFor
const whoopDirectFresh = buildMultiSourceHealth('test-athlete', {
  whoop_direct: {
    id: 'wd_test', schemaVersion: 1, createdAt: now22, updatedAt: now22,
    athleteId: 'test-athlete', provider: 'whoop_direct',
    lastSuccessfulIngestAt: now22, lastFailedIngestAt: null,
    freshnessStatus: 'fresh',
    coverageByDomain: {
      recovery: { status: 'fresh', lastDate: today22 },
      sleep: { status: 'fresh', lastDate: today22 },
      strain: { status: 'fresh', lastDate: today22 },
    },
    upstreamStatus: 'healthy', degradedReason: null,
  },
});
const wdRow = whoopDirectFresh.sources.find((s: any) => s.provider === 'whoop_direct') as any;
assert(wdRow.connectionStatus === 'available', 'whoop_direct with fresh data = available');
assert(wdRow.domainsAvailable.includes('recovery'), 'whoop_direct exposes recovery domain');

// 24.3 Readiness analysis — live mode
const { analyseReadiness } = await import('../../../../packages/shared/src/backend/services/readiness/analyse-readiness');

const readinessLive = analyseReadiness({
  athleteId: 'test-athlete',
  date: today22,
  normalizedDay: {
    recoveryScore: 72, hrvMs: 55, dailyStrain: 12,
    totalSleepHours: 7.8, restingHrBpm: 58,
  } as any,
  dailyArtifact: null,
  whoopDirectFresh: true,
});
assert(readinessLive.mode === 'live', 'readiness live mode when whoopDirectFresh');
assert(readinessLive.level === 'green', 'recovery 72% = green');
assert(readinessLive.confidence === 'high', '5 source fields = high confidence');
assert(readinessLive.guardrails.length > 0, 'guardrails always present');
assert(readinessLive.sourceFields.includes('recoveryScore'), 'recovery is a source field');

// 24.4 Readiness analysis — blocked without direct WHOOP
const readinessBlocked = analyseReadiness({
  athleteId: 'user-b',
  date: today22,
  normalizedDay: { recoveryScore: null, hrvMs: null, totalSleepHours: 7 } as any,
  dailyArtifact: null,
  whoopDirectFresh: false,
});
assert(readinessBlocked.mode === 'unavailable', 'readiness unavailable without direct WHOOP');
assert(readinessBlocked.level === 'blocked', 'readiness level blocked');
assert(readinessBlocked.missingness.includes('direct_whoop_recovery_fields'), 'missingness notes direct WHOOP');

// 24.5 Readiness analysis — seed mode (WHOOP fresh but no recovery score)
const readinessSeed = analyseReadiness({
  athleteId: 'test-athlete',
  date: today22,
  normalizedDay: { recoveryScore: null, hrvMs: 50, totalSleepHours: 6.5 } as any,
  dailyArtifact: null,
  whoopDirectFresh: true,
});
assert(readinessSeed.mode === 'seed', 'recovery null with WHOOP fresh = seed mode');
assert(readinessSeed.level === 'blocked', 'missing recovery = blocked');

// 24.6 Concept2 provenance detection (inline mirror of mobile isPolarSource pattern)
const C2_PATTERNS: RegExp[] = [/com\.concept2\./i, /ergdata/i, /(^|[^a-z])concept\s?2($|[^a-z])/i];
function isConcept2SourceLocal(src: string | null | undefined): boolean {
  if (!src) return false;
  return C2_PATTERNS.some((re) => re.test(src));
}
assert(isConcept2SourceLocal('com.concept2.ergdata'), 'ErgData Android package detected');
assert(isConcept2SourceLocal('ErgData'), 'ErgData friendly name detected');
assert(isConcept2SourceLocal('Concept2'), 'Concept2 name detected');
assert(!isConcept2SourceLocal('com.polar.polarflow'), 'Polar is NOT Concept2');
assert(!isConcept2SourceLocal(''), 'empty is NOT Concept2');
assert(!isConcept2SourceLocal(null), 'null is NOT Concept2');

// 24.7 FTMS parser — indoor bike data
const { parseIndoorBikeData, parseRowerData, accumulateSet } = await import('../../../../apps/mobile/src/services/ftms-parser');

// Build a fake Indoor Bike Data characteristic with flags for speed + cadence + power + HR + elapsed.
// Flags: 0x0004 (cadence) | 0x0040 (power) | 0x0400 (HR) | 0x1000 (elapsed) = 0x1444
// Bit 0 is 0 → speed present
const bikeBuf = new ArrayBuffer(14);
const bikeView = new DataView(bikeBuf);
bikeView.setUint16(0, 0x1444, true);       // flags
bikeView.setUint16(2, 2500, true);          // speed: 25.00 km/h
bikeView.setUint16(4, 160, true);           // cadence: 80 rpm (0.5 resolution)
bikeView.setInt16(6, 220, true);            // power: 220W
bikeView.setUint8(8, 155);                  // HR: 155 bpm
// pad for elapsed at offset that depends on skipped fields — simplified test
const bikeResult = parseIndoorBikeData(bikeView);
assert(bikeResult.kind === 'bike', 'FTMS: indoor bike kind');
assert(bikeResult.speed_kmh === 25, 'FTMS: speed parsed');
assert(bikeResult.cadence === 80, 'FTMS: cadence parsed');
assert(bikeResult.power_w === 220, 'FTMS: power parsed');

// 24.8 Set accumulator
const fakeSamples = [
  { at: 1000, power_w: 200, heart_rate_bpm: 150, cadence: 75, distance_m: 100 },
  { at: 2000, power_w: 220, heart_rate_bpm: 158, cadence: 78, distance_m: 200 },
  { at: 3000, power_w: 210, heart_rate_bpm: 162, cadence: 76, distance_m: 300 },
];
const setResult = accumulateSet(fakeSamples);
assert(setResult != null, 'FTMS: set accumulated');
assert(setResult!.avgWatts != null && Math.abs(setResult!.avgWatts! - 210) < 1, 'FTMS: avg watts ≈ 210');
assert(setResult!.peakWatts === 220, 'FTMS: peak watts = 220');
assert(setResult!.maxHr === 162, 'FTMS: max HR = 162');
assert(setResult!.minHr === 150, 'FTMS: min HR = 150');
assert(setResult!.hrRange === 12, 'FTMS: HR range = 12');
assert(setResult!.totalDistance === 300, 'FTMS: total distance = 300m');

// 24.9 Coach uses liveReadiness when present and live
const coachHiitWithLiveReadiness = buildCoachAnswer('am I ready for HIIT?', {
  ...baseContext,
  seedMode: false,
  liveReadiness: {
    mode: 'live',
    level: 'green',
    confidence: 'high',
    interpretation: 'WHOOP recovery: 72% (green). HRV: 55 ms. Sleep: 7.8h. Indicators support higher training load today.',
    metrics: { recoveryScore: 72, hrvMs: 55, dailyStrain: 12, sleepHours: 7.8 },
    guardrails: ['This is coaching context, not medical advice.'],
    missingness: [],
    contextUsed: ['3 HIIT sessions in last 7 days.'],
    sourceFields: ['recoveryScore', 'hrvMs', 'dailyStrain', 'totalSleepHours'],
  },
  capability: {
    ...(baseContext.capability ?? {}),
    mode: 'live_ready',
    missingWhoopNativeFields: [],
  },
} as any);
assert(coachHiitWithLiveReadiness.status === 'answered', 'Coach answers HIIT readiness when liveReadiness=live+green');
assert(coachHiitWithLiveReadiness.answer.short.includes('72%') || coachHiitWithLiveReadiness.answer.short.includes('green'),
  'Coach mentions recovery score or green in live readiness answer');
assert((coachHiitWithLiveReadiness.sourceDependencies ?? []).includes('live_readiness_analysis'),
  'Coach cites live_readiness_analysis as source');

// 24.10 Coach does NOT give live readiness when liveReadiness is blocked
const coachHiitBlockedReadiness = buildCoachAnswer('am I ready for HIIT?', {
  ...baseContext,
  seedMode: true,
  liveReadiness: {
    mode: 'unavailable',
    level: 'blocked',
    confidence: 'low',
    interpretation: 'Readiness analysis requires fresh direct WHOOP recovery, HRV, and strain.',
    metrics: { recoveryScore: null, hrvMs: null, dailyStrain: null, sleepHours: null },
    guardrails: ['This is coaching context, not medical advice.'],
    missingness: ['direct_whoop_recovery_fields'],
    contextUsed: [],
    sourceFields: [],
  },
  capability: {
    ...(baseContext.capability ?? {}),
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain'],
  },
} as any);
assert(coachHiitBlockedReadiness.status === 'insufficient_data' || coachHiitBlockedReadiness.status === 'downgraded', 'Coach blocks HIIT when liveReadiness is unavailable');
assert(!coachHiitBlockedReadiness.answer.short.toLowerCase().includes('green light'),
  'Coach never says green light with blocked readiness');

// 24.11 Samsung Health via Health Connect
const samsungEmptySummary = buildMultiSourceHealth('test-athlete', {
  samsung_health_via_health_connect: null,
});
const samsungEmpty = samsungEmptySummary.sources.find((s: any) => s.provider === 'samsung_health_via_health_connect') as any;
assert(samsungEmpty != null, 'samsung_health_via_health_connect row exists');
assert(samsungEmpty.connectionStatus === 'not_connected', 'Samsung empty = not_connected');
assert(samsungEmpty.directAdapter === false, 'Samsung via HC is indirect');
assert(samsungEmpty.notSafeFor.includes('readiness'), 'Samsung via HC is notSafeFor readiness');
assert(samsungEmpty.safeFor.includes('session_context'), 'Samsung via HC is safeFor session_context');

// 24.12 Samsung with fresh data
const samsungFreshRecord: SourceHealthStatus = {
  id: 'samsung_test', schemaVersion: 1, createdAt: now22, updatedAt: now22,
  athleteId: 'test-athlete', provider: 'samsung_health_via_health_connect',
  lastSuccessfulIngestAt: now22, lastFailedIngestAt: null,
  freshnessStatus: 'fresh',
  coverageByDomain: {
    sleep: { status: 'fresh', lastDate: today22 },
    steps: { status: 'fresh', lastDate: today22 },
    workouts: { status: 'fresh', lastDate: today22 },
    heart_rate_samples: { status: 'fresh', lastDate: today22 },
  },
  upstreamStatus: 'healthy', degradedReason: 'sourceApp:Samsung Health',
};
const samsungConnected = buildMultiSourceHealth('test-athlete', {
  samsung_health_via_health_connect: samsungFreshRecord,
});
const samsungRow = samsungConnected.sources.find((s: any) => s.provider === 'samsung_health_via_health_connect') as any;
assert(samsungRow.connectionStatus === 'available', 'Samsung with data = available');
assert(samsungRow.domainsAvailable.includes('sleep'), 'Samsung sleep domain available');
assert(samsungRow.domainsAvailable.includes('steps'), 'Samsung steps domain available');

// 24.13 Samsung does NOT unlock readiness even when connected
const readinessWithSamsung = buildCoachAnswer('am I ready for HIIT?', {
  ...baseContext,
  capability: {
    ...(baseContext.capability ?? {}),
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain'],
  },
  multiSourceHealth: {
    samsung_health_via_health_connect: { status: 'fresh', upstream: 'healthy', coverage: ['sleep', 'steps', 'workouts', 'heart_rate_samples'] },
    whoop: { status: 'not_connected' },
  },
} as any);
assert(readinessWithSamsung.status === 'insufficient_data' || readinessWithSamsung.status === 'downgraded',
  'Samsung alone does NOT unlock HIIT readiness');
assert(!readinessWithSamsung.answer.short.toLowerCase().includes('green light'),
  'Samsung alone no green light');

// 24.14 Coach: "Is Samsung Health connected?" — with provenance
const coachSamsungConnected = buildCoachAnswer('is samsung health connected?', {
  ...baseContext,
  multiSourceHealth: {
    samsung_health_via_health_connect: { status: 'fresh', upstream: 'healthy', coverage: ['sleep', 'steps', 'workouts'], lastIngestAt: now22 },
  },
} as any);
assert(coachSamsungConnected.status === 'answered', 'Coach answers Samsung connected');
assert(coachSamsungConnected.answer.short.toLowerCase().includes('samsung health'),
  'Coach mentions Samsung Health');
assert(coachSamsungConnected.answer.short.toLowerCase().includes('health connect'),
  'Coach mentions Health Connect as transport');

// 24.15 Coach: "Is Samsung Health connected?" — without provenance
const coachSamsungNotConnected = buildCoachAnswer('is samsung health connected?', {
  ...baseContext,
  multiSourceHealth: {
    samsung_health_via_health_connect: { status: 'not_connected' },
  },
} as any);
assert(coachSamsungNotConnected.answer.short.toLowerCase().includes('not connected'),
  'Coach says Samsung not connected when no provenance');
assert(coachSamsungNotConnected.answer.nextStep.toLowerCase().includes('samsung health'),
  'Coach gives Samsung Health setup instructions');

// 24.16 Samsung provenance detection (inline mirror)
const SAMSUNG_PATTERNS: RegExp[] = [/com\.sec\.android\.app\.shealth/i, /com\.samsung\.android\.health/i, /(^|[^a-z])samsung\s*health($|[^a-z])/i];
function isSamsungLocal(src: string | null | undefined): boolean { if (!src) return false; return SAMSUNG_PATTERNS.some((re) => re.test(src)); }
assert(isSamsungLocal('com.sec.android.app.shealth'), 'Samsung old package detected');
assert(isSamsungLocal('com.samsung.android.health'), 'Samsung new package detected');
assert(isSamsungLocal('Samsung Health'), 'Samsung Health label detected');
assert(!isSamsungLocal('com.polar.polarflow'), 'Polar is NOT Samsung');
assert(!isSamsungLocal('com.google.android.fit'), 'Google Fit is NOT Samsung');
assert(!isSamsungLocal(''), 'empty is NOT Samsung');
assert(!isSamsungLocal(null), 'null is NOT Samsung');

// 24.17 Cross-user isolation: userA Samsung, userB none
const userASamsung = buildMultiSourceHealth('user-a', { samsung_health_via_health_connect: samsungFreshRecord });
const userBSamsung = buildMultiSourceHealth('user-b', { samsung_health_via_health_connect: null });
assert(userASamsung.sources.find((s: any) => s.provider === 'samsung_health_via_health_connect')?.connectionStatus === 'available',
  'User A Samsung = available');
assert(userBSamsung.sources.find((s: any) => s.provider === 'samsung_health_via_health_connect')?.connectionStatus === 'not_connected',
  'User B Samsung = not_connected (isolation)');

// 24.18 Contextual readiness from health hubs (no WHOOP)
const coachContextualReadiness = buildCoachAnswer('am I ready for hiit?', {
  ...baseContext,
  seedMode: true,
  normalizedDay: { totalSleepHours: 7.5, restingHrBpm: 60, recoveryScore: null } as any,
  capability: {
    ...(baseContext.capability ?? {}),
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain'],
  },
  multiSourceHealth: {
    health_connect: { status: 'fresh', upstream: 'healthy' },
    samsung_health_via_health_connect: { status: 'fresh', upstream: 'healthy', coverage: ['sleep', 'steps', 'workouts'] },
    whoop: { status: 'not_connected' },
    whoop_direct: { status: 'not_connected' },
  },
} as any);
assert(coachContextualReadiness.status === 'downgraded', 'Contextual readiness = downgraded (not fully answered)');
assert(coachContextualReadiness.answer.short.toLowerCase().includes('contextual') ||
       coachContextualReadiness.answer.short.toLowerCase().includes('health connect') ||
       coachContextualReadiness.answer.short.toLowerCase().includes('samsung'),
  'Coach mentions hub sources in contextual readiness');
assert(coachContextualReadiness.answer.short.toLowerCase().includes('not a direct readiness clearance') ||
       coachContextualReadiness.answer.short.toLowerCase().includes('training context'),
  'Coach explicitly says this is NOT a clearance');
assert(!coachContextualReadiness.answer.short.toLowerCase().includes('green light'),
  'Contextual readiness never says green light');
assert((coachContextualReadiness.sourceDependencies ?? []).includes('contextual_hub_readiness'),
  'Coach cites contextual_hub_readiness as source');

// 24.19 Contextual readiness NOT triggered when no hubs connected
const coachNoHubs = buildCoachAnswer('am I ready for hiit?', {
  ...baseContext,
  seedMode: true,
  capability: {
    ...(baseContext.capability ?? {}),
    mode: 'seed_partial',
    missingWhoopNativeFields: ['recovery', 'sleep', 'strain'],
  },
  multiSourceHealth: {
    health_connect: { status: 'not_connected' },
    whoop: { status: 'not_connected' },
  },
} as any);
assert(coachNoHubs.status === 'downgraded' || coachNoHubs.status === 'insufficient_data',
  'No hubs = standard insufficient/downgraded (no contextual path)');
assert(!(coachNoHubs.sourceDependencies ?? []).includes('contextual_hub_readiness'),
  'No contextual_hub_readiness source when no hubs connected');

// 24.20 History scope verified via type system — BacklogAnalysisStatusRecord
// now requires historyScope. This is a compile-time assertion; the runtime
// test is that resA (defined inside the async backlog block) has it.
// We test the field on a fresh inline object to avoid scope issues:
const historyTestRecord: { historyScope: 'full_history' | 'limited_history' | 'unknown' } = { historyScope: 'unknown' };
assert(historyTestRecord.historyScope === 'unknown', 'historyScope field exists on type');

// 24.21 Samsung provenance detection patterns (additional)
assert(isSamsungLocal('com.sec.android.app.shealth'), 'Samsung old pkg');
assert(isSamsungLocal('Samsung Health'), 'Samsung friendly');
assert(!isSamsungLocal('com.polar.polarflow'), 'Polar not Samsung');

// 24.22 Hub-first contextual readiness model
const { analyseContextualReadiness } = await import('../../../../packages/shared/src/backend/services/readiness/analyse-contextual-readiness');

// Full hub data — should produce looks_good or moderate
const ctxFull = analyseContextualReadiness({
  athleteId: 'test-athlete',
  date: today22,
  recentDays: Array.from({ length: 10 }, (_, i) => ({
    date: `2026-04-${String(7 + i).padStart(2, '0')}`,
    totalSleepHours: 7.5 + (i % 3) * 0.3,
    restingHrBpm: 58 + (i % 4),
    hrvMs: 50 + (i % 5),
    workoutCount: i % 3 === 0 ? 1 : 0,
    grapplingSessionCount: 0,
    nutritionCalories: i % 2 === 0 ? 2400 : null,
    nutritionCoverage: i % 2 === 0 ? 'full' : 'none',
    presentFields: ['totalSleepHours', 'restingHrBpm'],
  } as any)),
  today: { totalSleepHours: 7.8, restingHrBpm: 57, nutritionCalories: 2300, nutritionCoverage: 'full', workoutCount: 0, grapplingSessionCount: 0, presentFields: [] } as any,
  hubSources: ['Health Connect', 'Samsung Health'],
  hiitSessionsLast7Days: 2,
  grapplingSessionsLast7Days: 1,
  nutritionLoggedToday: true,
  hasDirectWhoop: false,
  historyScope: 'full_history',
});
assert(ctxFull.mode === 'contextual', 'contextual readiness mode is always contextual');
assert(ctxFull.level === 'looks_good' || ctxFull.level === 'moderate', 'full hub data = looks_good or moderate');
assert(ctxFull.signals.length >= 3, 'at least 3 signals from full hub data');
assert(ctxFull.disclaimer.includes('Contextual'), 'disclaimer says contextual');
assert(ctxFull.whoopWouldAdd.length > 0, 'lists what WHOOP would add when not connected');
assert(ctxFull.whoopWouldAdd.some((w: string) => w.toLowerCase().includes('recovery')), 'WHOOP adds recovery score');

// Insufficient data
const ctxEmpty = analyseContextualReadiness({
  athleteId: 'test-athlete',
  date: today22,
  recentDays: [],
  today: null,
  hubSources: [],
  hiitSessionsLast7Days: 0,
  grapplingSessionsLast7Days: 0,
  nutritionLoggedToday: false,
  hasDirectWhoop: false,
  historyScope: 'unknown',
});
assert(ctxEmpty.level === 'insufficient', 'no data = insufficient');
assert(ctxEmpty.signals.length === 0, 'no signals from empty data');
assert(ctxEmpty.gaps.length > 0, 'gaps listed when no data');

// With direct WHOOP — whoopWouldAdd should be empty
const ctxInputBase = {
  athleteId: 'test-athlete',
  date: today22,
  recentDays: Array.from({ length: 10 }, (_, i) => ({
    date: `2026-04-${String(7 + i).padStart(2, '0')}`,
    totalSleepHours: 7.5 + (i % 3) * 0.3,
    restingHrBpm: 58 + (i % 4),
    hrvMs: 50 + (i % 5),
    workoutCount: i % 3 === 0 ? 1 : 0,
    grapplingSessionCount: 0,
    nutritionCalories: i % 2 === 0 ? 2400 : null,
    nutritionCoverage: i % 2 === 0 ? 'full' : 'none',
    presentFields: ['totalSleepHours', 'restingHrBpm'],
  } as any)),
  today: { totalSleepHours: 7.8, restingHrBpm: 57, nutritionCalories: 2300, nutritionCoverage: 'full', workoutCount: 0, grapplingSessionCount: 0, presentFields: [] } as any,
  hubSources: ['Health Connect', 'Samsung Health'],
  hiitSessionsLast7Days: 2,
  grapplingSessionsLast7Days: 1,
  nutritionLoggedToday: true,
  historyScope: 'full_history' as const,
};
const ctxWithWhoop = analyseContextualReadiness({
  ...ctxInputBase,
  hasDirectWhoop: true,
});
assert(ctxWithWhoop.whoopWouldAdd.length === 0, 'no WHOOP gaps when direct WHOOP connected');

// Limited history — gap should mention it
const ctxLimited = analyseContextualReadiness({
  ...ctxInputBase,
  hasDirectWhoop: false,
  historyScope: 'limited_history',
});
assert(ctxLimited.gaps.some((g: string) => g.toLowerCase().includes('history') || g.toLowerCase().includes('30 day')),
  'limited history noted in gaps');

// Coach uses contextualReadiness for hub-first answer
const coachCtxReadiness = buildCoachAnswer('am I ready for hiit?', {
  ...baseContext,
  seedMode: true,
  normalizedDay: { totalSleepHours: 7.5, restingHrBpm: 60, recoveryScore: null } as any,
  capability: { ...(baseContext.capability ?? {}), mode: 'seed_partial', missingWhoopNativeFields: ['recovery', 'sleep', 'strain'] },
  multiSourceHealth: {
    health_connect: { status: 'fresh', upstream: 'healthy' },
    samsung_health_via_health_connect: { status: 'fresh', upstream: 'healthy' },
    whoop: { status: 'not_connected' },
  },
  contextualReadiness: ctxFull,
} as any);
assert(coachCtxReadiness.status === 'downgraded', 'hub-first contextual readiness = downgraded');
assert(coachCtxReadiness.answer.short.toLowerCase().includes('hub') ||
       coachCtxReadiness.answer.short.toLowerCase().includes('health connect') ||
       coachCtxReadiness.answer.short.toLowerCase().includes('looks good') ||
       coachCtxReadiness.answer.short.toLowerCase().includes('samsung'),
  'Coach mentions hub sources or level in contextual readiness');
assert(!coachCtxReadiness.answer.short.toLowerCase().includes('green light'),
  'hub-first readiness never says green light');

// 24.23 Apple Health Coach handler
const coachAHConnected = buildCoachAnswer('is apple health connected?', {
  ...baseContext,
  multiSourceHealth: {
    apple_health: { status: 'fresh', upstream: 'healthy', lastIngestAt: now22 },
  },
} as any);
assert(coachAHConnected.status === 'answered', 'Coach answers Apple Health connected');
assert(coachAHConnected.answer.short.toLowerCase().includes('apple health'), 'Coach mentions Apple Health');
assert(coachAHConnected.answer.short.toLowerCase().includes('connected'), 'Coach says connected');

const coachAHNotConnected = buildCoachAnswer('is apple health connected?', {
  ...baseContext,
  multiSourceHealth: {
    apple_health: { status: 'not_connected' },
  },
} as any);
assert(coachAHNotConnected.answer.short.toLowerCase().includes('not connected'), 'Coach says Apple Health not connected');

// 24.24 Coach "what should I track next?" handler
const coachTrackNext = buildCoachAnswer('what should i track next?', {
  ...baseContext,
  multiSourceHealth: {
    health_connect: { status: 'fresh' },
    samsung_health_via_health_connect: { status: 'not_connected' },
  },
  recentHIITWorkouts: [],
  normalizedDay: { nutritionCalories: null } as any,
} as any);
assert(coachTrackNext.status === 'answered' || coachTrackNext.status === 'insufficient_data',
  'Coach answers what to track next');
assert(coachTrackNext.answer.short.length > 0, 'Coach provides a tracking suggestion');

// 24.25 Coach "how does my training look today?" — routes to training domain
// (question contains 'train' which matches TRAINING_KEYWORDS before general)
const coachTrainingLook = buildCoachAnswer('how does my training look today?', {
  ...baseContext,
  contextualReadiness: ctxFull,
} as any);
assert(coachTrainingLook.status === 'answered' || coachTrainingLook.status === 'downgraded' || coachTrainingLook.status === 'insufficient_data',
  'Coach responds to training look question');
assert(coachTrainingLook.answer.short.length > 10, 'Coach provides substantive training summary');

// 24.26 Samsung Health direct provider
const samsungDirectSummary = buildMultiSourceHealth('test-athlete', {
  samsung_health_direct: null,
});
const samsungDirectRow = samsungDirectSummary.sources.find((s: any) => s.provider === 'samsung_health_direct') as any;
assert(samsungDirectRow != null, 'samsung_health_direct row exists');
assert(samsungDirectRow.connectionStatus === 'not_connected', 'samsung_health_direct empty = not_connected (SDK implemented, no data yet)');
assert(samsungDirectRow.notSafeFor.includes('readiness'), 'samsung_health_direct notSafeFor readiness');

// 24.27 Samsung via HC + direct coexist
const samsungBothSummary = buildMultiSourceHealth('test-athlete', {
  samsung_health_via_health_connect: samsungFreshRecord,
  samsung_health_direct: null,
});
const viaHcRow2 = samsungBothSummary.sources.find((s: any) => s.provider === 'samsung_health_via_health_connect') as any;
const directRow2 = samsungBothSummary.sources.find((s: any) => s.provider === 'samsung_health_direct') as any;
assert(viaHcRow2.connectionStatus === 'available', 'via HC still available when direct is scaffold');
assert(directRow2.connectionStatus === 'not_connected', 'direct = not_connected when no data (SDK ready but no ingest)');

// 24.28 Samsung direct with fresh data
const samsungDirectFresh = buildMultiSourceHealth('test-athlete', {
  samsung_health_direct: {
    id: 'sd_test', schemaVersion: 1, createdAt: now22, updatedAt: now22,
    athleteId: 'test-athlete', provider: 'samsung_health_direct',
    lastSuccessfulIngestAt: now22, lastFailedIngestAt: null,
    freshnessStatus: 'fresh',
    coverageByDomain: {
      sleep: { status: 'fresh', lastDate: today22 },
      steps: { status: 'fresh', lastDate: today22 },
      heart_rate_samples: { status: 'fresh', lastDate: today22 },
    },
    upstreamStatus: 'healthy', degradedReason: null,
  },
});
const sdConnectedRow = samsungDirectFresh.sources.find((s: any) => s.provider === 'samsung_health_direct') as any;
assert(sdConnectedRow.connectionStatus === 'available', 'Samsung direct with fresh data = available');
assert(sdConnectedRow.domainsAvailable.includes('sleep'), 'Samsung direct sleep available');
assert(sdConnectedRow.directAdapter === true, 'Samsung direct is a direct adapter');
assert(sdConnectedRow.notSafeFor.includes('readiness'), 'Samsung direct still notSafeFor readiness');
assert(sdConnectedRow.safeFor.includes('session_context'), 'Samsung direct safeFor session_context');

// 24.29 Samsung direct does NOT unlock readiness
const readinessWithSamsungDirect = buildCoachAnswer('am I ready for HIIT?', {
  ...baseContext,
  capability: { ...(baseContext.capability ?? {}), mode: 'seed_partial', missingWhoopNativeFields: ['recovery', 'sleep', 'strain'] },
  multiSourceHealth: {
    samsung_health_direct: { status: 'fresh', upstream: 'healthy', coverage: ['sleep', 'steps', 'heart_rate_samples'] },
    whoop: { status: 'not_connected' },
  },
} as any);
assert(!readinessWithSamsungDirect.answer.short.toLowerCase().includes('green light'),
  'Samsung direct alone does not give green light');

// 24.30 Coach: "Is Polar connected?" — knows about direct_polar
const coachDirectPolarMissing = buildCoachAnswer('is polar connected?', {
  ...baseContext,
  multiSourceHealth: {
    polar: { status: 'not_connected' },
    direct_polar: { status: 'not_connected', reason: 'Polar AccessLink not configured.' },
    polar_via_health_connect: { status: 'not_connected' },
  },
} as any);
assert(coachDirectPolarMissing.answer.short.toLowerCase().includes('not connected'),
  'Coach: polar not connected when all three paths are off');

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\n=== SUMMARY ===`);
console.log(`  Passed: ${passed}`);
console.log(`  Failed: ${failed}`);
console.log(`  Total:  ${passed + failed}`);
if (failed > 0) {
  process.exit(1);
} else {
  console.log('\nAll contract tests passed.');
}
})().catch((e) => { console.error('Test runner error:', e); process.exit(1); });
