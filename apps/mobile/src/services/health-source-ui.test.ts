import {
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
assertEqual(getWhoopDirectStateLabel('partial', { awaitingCycle: true }).label, 'WHOOP Direct awaiting cycle', 'WHOOP awaiting label');
assertEqual(getPolarDirectStateLabel(false).label, 'Polar Direct setup needed', 'Polar setup label');

const seed = getReadinessSeedBadge({ hasLiveWhoopRecovery: false, confidenceLevel: 'low' });
assertEqual(seed.label, 'Seed', 'Seed badge label');
assertEqual(seed.provisional, true, 'Seed badge provisional flag');
assertMatches(seed.note, /Provisional/, 'Seed badge note');

const live = getReadinessSeedBadge({ hasLiveWhoopRecovery: true });
assertEqual(live.label, 'Live', 'Live badge label');
assertEqual(live.provisional, false, 'Live badge provisional flag');
