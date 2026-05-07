import {
  buildHubReadinessEvidence,
  getNativeHealthSourceCopy,
  getPolarDirectStateLabel,
  getReadinessSeedBadge,
  getWhoopDirectStateLabel,
} from './health-source-ui';

function assertEqual(actual: unknown, expected: unknown, message: string): void {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

function assertMatches(actual: string, pattern: RegExp, message: string): void {
  if (!pattern.test(actual)) {
    throw new Error(`${message}: ${actual}`);
  }
}

assertEqual(getNativeHealthSourceCopy('ios').sourceName, 'Apple Health / HealthKit', 'iOS native source name');
assertEqual(getNativeHealthSourceCopy('ios').hubLabel, 'Apple Health / HealthKit hub data', 'iOS hub label');
assertEqual(getNativeHealthSourceCopy('android').sourceName, 'Health Connect', 'Android native source name');
assertEqual(getNativeHealthSourceCopy('android').hubLabel, 'Health Connect hub data', 'Android hub label');

assertEqual(getWhoopDirectStateLabel('config_missing').label, 'WHOOP Direct setup needed', 'WHOOP setup label');
assertEqual(getWhoopDirectStateLabel('connected').state, 'connected', 'WHOOP connected state');
assertEqual(getWhoopDirectStateLabel('permission_needed').state, 'permission_needed', 'WHOOP permission-needed state');
assertEqual(getWhoopDirectStateLabel('sync_failed').state, 'sync_failed', 'WHOOP sync-failed state');
assertEqual(getWhoopDirectStateLabel('partial', { awaitingCycle: true }).label, 'WHOOP Direct awaiting cycle', 'WHOOP awaiting label');
assertEqual(getPolarDirectStateLabel(false).label, 'Polar AccessLink planned', 'Polar planned label');

const seed = getReadinessSeedBadge({ hasLiveWhoopRecovery: false, confidenceLevel: 'low' });
assertEqual(seed.label, 'Seed', 'Seed badge label');
assertEqual(seed.provisional, true, 'Seed badge provisional flag');
assertMatches(seed.note, /Provisional/, 'Seed badge note');

const live = getReadinessSeedBadge({ hasLiveWhoopRecovery: true });
assertEqual(live.label, 'Seed', 'WHOOP evidence keeps readiness seed-labelled');
assertEqual(live.provisional, true, 'WHOOP evidence keeps readiness provisional');
assertMatches(live.note, /optional evidence only/, 'WHOOP evidence note');

const hubEvidence = buildHubReadinessEvidence({
  platform: 'android',
  fields: {
    hrv: 44,
    restingHr: 58,
    sleepHours: 7.2,
    activeCalories: 550,
    workouts: 1,
  },
  provenance: ['com.polar.flow'],
  polarHubDetected: true,
  manualSessionData: true,
  journalContext: true,
});
assertEqual(hubEvidence.confidence, 'high', 'Hub readiness high confidence');
assertMatches(hubEvidence.sourceLabels.join(' | '), /Health Connect hub data/, 'Hub readiness native source');
assertMatches(hubEvidence.sourceLabels.join(' | '), /Polar via Health Connect/, 'Hub readiness polar provenance');
assertMatches(hubEvidence.sourceLabels.join(' | '), /Daily journal/, 'Hub readiness journal source');
assertMatches(hubEvidence.inputLabels.join(' | '), /subjective check-in/, 'Hub readiness journal input');

const cappedEvidence = buildHubReadinessEvidence({
  platform: 'ios',
  fields: {
    hrv: 55,
    restingHr: 52,
    sleepHours: 8,
    activeCalories: 400,
    workouts: 1,
  },
  journalContext: true,
  activeMetricAffectingJournalItems: 2,
});
assertEqual(cappedEvidence.confidence, 'low', 'Multiple active journal items cap readiness confidence');
assertMatches(cappedEvidence.note, /Multiple tracked items active/, 'Journal confidence cap note');

const missingEvidence = buildHubReadinessEvidence({
  platform: 'ios',
  fields: {
    sleepHours: null,
    hrv: null,
    restingHr: 55,
    activeCalories: null,
    workouts: 0,
  },
  insufficientHistory: true,
});
assertEqual(missingEvidence.confidence, 'low', 'Hub readiness low confidence');
assertMatches(missingEvidence.missingLabels.join(' | '), /sleep/, 'Hub readiness missing sleep');
assertMatches(missingEvidence.missingLabels.join(' | '), /history baseline/, 'Hub readiness missing history');
