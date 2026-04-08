/**
 * Platform-agnostic health service factory.
 *
 * EXPO GO SAFETY:
 * This file is the ONLY entry point for health services.
 * It NEVER directly requires native modules at the top level.
 *
 * In Expo Go: returns the STUB immediately. The native files
 * (health.ios.ts, health.android.ts) are never loaded.
 *
 * In dev builds: lazily loads native modules via require().
 */
import { Platform } from 'react-native';
import { isExpoGo } from './expo-detect';
import type { IHealthService } from '@lauburu/shared';

let _instance: IHealthService | null = null;

export function getHealthService(): IHealthService {
  if (_instance) return _instance;

  if (isExpoGo()) {
    _instance = STUB;
    return _instance;
  }

  // Only in native dev builds — load native modules
  _instance = loadNative();
  return _instance;
}

function loadNative(): IHealthService {
  try {
    if (Platform.OS === 'ios') {
      // This require is only reached in dev builds, never in Expo Go.
      // health.ios.ts uses lazy require() for the native healthkit package.
      const { HealthKitService } = require('./health.ios');
      return new HealthKitService();
    }
    if (Platform.OS === 'android') {
      const { HealthConnectService } = require('./health.android');
      return new HealthConnectService();
    }
  } catch (e) {
    console.warn('Native health module unavailable:', e);
  }
  return STUB;
}

/** Safe stub — works everywhere, returns "unavailable" for all metrics */
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
