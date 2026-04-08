/**
 * Platform-agnostic health service factory.
 *
 * EXPO GO SAFETY:
 * 1. isExpoGo() is in a separate file (expo-detect.ts) with no native deps
 * 2. metro.config.js blocks native health packages from the bundle
 * 3. Runtime guard returns stub before any native code path
 */
import { Platform } from 'react-native';
import { isExpoGo } from './expo-detect';
import type { IHealthService } from '@lauburu/shared';

// Re-export for use in UI components
export { isExpoGo };

let _instance: IHealthService | null = null;

export function getHealthService(): IHealthService {
  if (_instance) return _instance;

  if (isExpoGo()) {
    _instance = STUB;
    return _instance;
  }

  try {
    if (Platform.OS === 'ios') {
      const { HealthKitService } = require('./health.ios');
      _instance = new HealthKitService();
    } else if (Platform.OS === 'android') {
      const { HealthConnectService } = require('./health.android');
      _instance = new HealthConnectService();
    } else {
      _instance = STUB;
    }
  } catch (e) {
    console.warn('Native health module unavailable:', e);
    _instance = STUB;
  }

  return _instance!;
}

const STUB: IHealthService = {
  isAvailable: async () => false,
  checkPermissions: async () => ({
    available: false,
    permissions: {
      heart_rate: 'unavailable' as const,
      resting_heart_rate: 'unavailable' as const,
      hrv: 'unavailable' as const,
      sleep: 'unavailable' as const,
      steps: 'unavailable' as const,
      active_calories: 'unavailable' as const,
      workouts: 'unavailable' as const,
    },
  }),
  requestPermissions: async () => ({
    available: false,
    permissions: {
      heart_rate: 'unavailable' as const,
      resting_heart_rate: 'unavailable' as const,
      hrv: 'unavailable' as const,
      sleep: 'unavailable' as const,
      steps: 'unavailable' as const,
      active_calories: 'unavailable' as const,
      workouts: 'unavailable' as const,
    },
  }),
  fetchSamples: async () => [],
  fetchWorkouts: async () => [],
  fetchSleep: async () => [],
};
