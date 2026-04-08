/**
 * Platform-agnostic health service factory.
 * Returns HealthKit on iOS, Health Connect on Android.
 *
 * EXPO GO SAFETY:
 * Native health modules (NitroModules) crash in Expo Go.
 * We detect Expo Go at runtime and return the unavailable stub instead.
 * Native modules only load in dev builds (`expo prebuild` + `expo run:ios`).
 */
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import type { IHealthService } from '@lauburu/shared';

let _instance: IHealthService | null = null;

/** True when running inside Expo Go (not a dev build or standalone) */
function isExpoGo(): boolean {
  return Constants.appOwnership === 'expo';
}

export { isExpoGo };

export function getHealthService(): IHealthService {
  if (_instance) return _instance;

  // In Expo Go, native health modules are not available — return stub
  if (isExpoGo()) {
    _instance = createUnavailableStub();
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
      _instance = createUnavailableStub();
    }
  } catch (e) {
    // Fallback if native module fails to load for any reason
    console.warn('Native health module unavailable:', e);
    _instance = createUnavailableStub();
  }

  return _instance!;
}

function createUnavailableStub(): IHealthService {
  const unavailable: Record<string, 'unavailable'> = {
    heart_rate: 'unavailable',
    resting_heart_rate: 'unavailable',
    hrv: 'unavailable',
    sleep: 'unavailable',
    steps: 'unavailable',
    active_calories: 'unavailable',
    workouts: 'unavailable',
  };
  return {
    isAvailable: async () => false,
    checkPermissions: async () => ({
      available: false,
      permissions: unavailable as any,
    }),
    requestPermissions: async () => ({
      available: false,
      permissions: unavailable as any,
    }),
    fetchSamples: async () => [],
    fetchWorkouts: async () => [],
    fetchSleep: async () => [],
  };
}
